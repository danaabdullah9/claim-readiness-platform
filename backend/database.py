import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "claimDB.db"
UPLOADS_DIR = BASE_DIR / "backend" / "uploads"

# القيم اللي يرجعها الـ AI أحيانًا بدل القيمة الفعلية
_EMPTY_VALUES = {"", "null", "none", "n/a", "na", "not found", "unknown", "-"}

_DATE_FORMATS = (
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%d %B %Y",
    "%d %b %Y",
    "%B %d, %Y",
)

# جدول Claims ما فيه أعمدة لـ PatientName / ClaimId / MemberId / نتيجة التدقيق
# (ممنوع تعديل السكيمة)، فنخزّنهم كسطر JSON أول داخل ClinicalSummary ونفكّه عند
# القراءة. الفصل يتم بالسطر الأول لأن الـ Discrepancies مصفوفة كائنات وممكن
# تحتوي أي رمز، فالاعتماد على الأقواس يكسر القراءة.
_META_PREFIX = "[Meta: "
_META_SUFFIX = "]"

# الصيغة القديمة قبل إضافة الـ Meta (نقرأها عشان المطالبات المخزّنة سابقًا)
_LEGACY_NAME_PREFIX = "[PatientName: "

# أرقام عربية-هندية + الفاصلة العشرية العربية
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

# عمود TotalAmount يخزّن ريال سعودي دائمًا. أي فاتورة بعملة أخرى تُحوَّل قبل
# الحفظ، ونحتفظ بالمبلغ والعملة الأصليين في الـ meta عشان يظهران للمدقق.
# ملاحظة: أسعار ثابتة (تقريبية) — لو احتجت أسعار لحظية، بدّل convert_to_sar
# باستدعاء مزوّد أسعار خارجي.
EXCHANGE_RATES_TO_SAR = {
    "SAR": 1.0,
    "USD": 3.75,
    "EUR": 4.05,
    "GBP": 4.75,
    "AED": 1.021,
    "QAR": 1.030,
    "KWD": 12.20,
    "BHD": 9.95,
    "OMR": 9.75,
    "JOD": 5.29,
    "EGP": 0.077,
    "TRY": 0.11,
    "INR": 0.045,
    "PKR": 0.0135,
    "LBP": 0.000042,
    "SDG": 0.0062,
    "YER": 0.015,
    "MAD": 0.375,
    "TND": 1.21,
    "DZD": 0.028,
    "IQD": 0.00286,
    "SYP": 0.00029,
    "CHF": 4.25,
    "CAD": 2.72,
    "AUD": 2.45,
    "JPY": 0.024,
    "CNY": 0.52,
}

# رموز ونصوص تظهر على الفواتير بدل كود العملة
_CURRENCY_ALIASES = {
    "﷼": "SAR", "ر.س": "SAR", "ريال": "SAR", "SR": "SAR", "SAUDI RIYAL": "SAR",
    "$": "USD", "US$": "USD", "دولار": "USD",
    "€": "EUR", "يورو": "EUR",
    "£": "GBP", "جنيه استرليني": "GBP",
    "د.إ": "AED", "درهم": "AED", "DHS": "AED",
    "ج.م": "EGP", "جنيه": "EGP",
    "د.ك": "KWD", "د.ب": "BHD", "ر.ع": "OMR", "ر.ق": "QAR", "د.أ": "JOD",
}


def normalize_currency(value, default="SAR"):
    """يحوّل ما كتبه الـ AI لكود عملة من ثلاثة أحرف."""
    text = _clean(value)
    if not text:
        return default

    upper = text.upper().strip()
    if upper in EXCHANGE_RATES_TO_SAR:
        return upper

    for alias, code in _CURRENCY_ALIASES.items():
        if alias.upper() in upper:
            return code

    # آخر محاولة: أول ثلاثة أحرف لو كانت كود معروف
    if len(upper) >= 3 and upper[:3] in EXCHANGE_RATES_TO_SAR:
        return upper[:3]

    return default


def convert_to_sar(amount, currency):
    """يرجع (المبلغ بالريال، كود العملة، سعر الصرف المستخدم)."""
    code = normalize_currency(currency)
    rate = EXCHANGE_RATES_TO_SAR.get(code)
    if rate is None:
        raise ValueError(
            f"Unsupported currency '{currency}'. Supported: "
            f"{', '.join(sorted(EXCHANGE_RATES_TO_SAR))}."
        )
    return round(amount * rate, 2), code, rate


class DuplicateClaimError(Exception):
    """المطالبة موجودة مسبقًا (InvoiceNumber مفهرس UNIQUE في قاعدة البيانات)."""

    def __init__(self, invoice_number, claim_id):
        super().__init__(f"Claim for invoice '{invoice_number}' already exists.")
        self.invoice_number = invoice_number
        self.claim_id = claim_id


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ClaimNotifications (
            NotificationID INTEGER PRIMARY KEY AUTOINCREMENT,
            ClaimID INTEGER NOT NULL,
            UserID INTEGER NOT NULL,
            NotificationType TEXT NOT NULL,
            Title TEXT NOT NULL,
            Message TEXT NOT NULL,
            CustomerStatus TEXT,
            CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ClaimID) REFERENCES Claims(ClaimID),
            FOREIGN KEY (UserID) REFERENCES USERS(user_ID)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ClaimDocumentFiles (
            DocumentID INTEGER PRIMARY KEY,
            StoredName TEXT NOT NULL,
            ContentType TEXT NOT NULL,
            FOREIGN KEY (DocumentID) REFERENCES Documents(DocumentID)
        )
    """)
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def _clean(value):
    """يرجع نص نظيف أو None لو القيمة فاضية أو placeholder من الـ AI."""
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in _EMPTY_VALUES:
        return None
    return text


def _require(value, field_name):
    cleaned = _clean(value)
    if cleaned is None:
        raise ValueError(f"Missing required field extracted from documents: {field_name}")
    return cleaned


def _parse_date(value, field_name="InvoiceDate"):
    """يحوّل التاريخ لصيغة ISO (YYYY-MM-DD) المتوقعة في عمود DATE."""
    text = _require(value, field_name)
    for date_format in _DATE_FORMATS:
        try:
            return datetime.strptime(text, date_format).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format for {field_name}: '{text}'")


def _parse_amount(value, field_name="TotalAmount"):
    """يشيل رمز العملة والفواصل ويرجع رقم عشري.

    النسخة القديمة كانت تشيل كل الرموز وتلصق الأرقام ببعض، فلو جت القيمة
    "1,500.00 + VAT 225.00" كانت تطلع 1500225 بدون أي خطأ. الحين نستخرج
    الأرقام كاملة ونرفض القيمة لو فيها أكثر من رقم واحد.
    """
    text = _require(value, field_name)
    text = text.translate(_ARABIC_DIGITS).replace("٫", ".").replace("٬", ",")

    numbers = re.findall(r"-?\d[\d,]*(?:\.\d+)?", text)
    if not numbers:
        raise ValueError(f"Unrecognized amount format for {field_name}: '{text}'")
    if len(numbers) > 1:
        raise ValueError(
            f"Ambiguous amount for {field_name}: '{text}' contains {len(numbers)} numbers. "
            "Expected a single total value."
        )

    try:
        return round(float(numbers[0].replace(",", "")), 2)
    except ValueError:
        raise ValueError(f"Unrecognized amount format for {field_name}: '{text}'")


def _provider_type(provider_name):
    """ProviderType عمود NOT NULL، فنشتقه من اسم المنشأة."""
    name = provider_name.lower()
    if "hospital" in name:
        return "Hospital"
    if "clinic" in name or "polyclinic" in name:
        return "Clinic"
    if "pharmacy" in name:
        return "Pharmacy"
    if "lab" in name:
        return "Laboratory"
    return "Medical Center"


def _claim_status(analysis):
    """ClaimStatus فيه CHECK constraint: Pending / Approved / Rejected فقط."""
    if analysis.get("is_valid") is False:
        return "Rejected"
    if str(analysis.get("match_status", "")).lower() == "rejected":
        return "Rejected"
    return "Pending"


def _pack_clinical_summary(meta, clinical_summary):
    """يدمج بيانات المستند ونتيجة التدقيق مع الملخص السريري في عمود واحد."""
    body = clinical_summary or ""
    meta = {key: value for key, value in (meta or {}).items() if value not in (None, "", [])}
    if not meta:
        return body or None

    header = f"{_META_PREFIX}{json.dumps(meta, ensure_ascii=False)}{_META_SUFFIX}"
    return f"{header}\n{body}" if body else header


def _unpack_clinical_summary(raw_value):
    """يرجع (meta_dict, ClinicalSummary) من القيمة المخزّنة."""
    if not raw_value:
        return {}, raw_value

    first_line, _, remainder = raw_value.partition("\n")

    if first_line.startswith(_META_PREFIX) and first_line.endswith(_META_SUFFIX):
        try:
            meta = json.loads(first_line[len(_META_PREFIX):-len(_META_SUFFIX)])
        except json.JSONDecodeError:
            return {}, raw_value
        return meta, (remainder or None)

    # الصيغة القديمة: [PatientName: ...]
    if first_line.startswith(_LEGACY_NAME_PREFIX) and first_line.endswith(_META_SUFFIX):
        patient_name = first_line[len(_LEGACY_NAME_PREFIX):-len(_META_SUFFIX)]
        return {"PatientName": patient_name}, (remainder or None)

    return {}, raw_value


# ---------------------------------------------------------------------------
# Table helpers
# ---------------------------------------------------------------------------

def resolve_user_id(conn, user_id=None, national_id=None):
    """يحدد UserID من المستخدم المسجّل دخوله أو من رقم الهوية المستخرج."""
    if user_id is not None:
        row = conn.execute(
            "SELECT user_ID FROM USERS WHERE user_ID = ?", (user_id,)
        ).fetchone()
        if row:
            return row["user_ID"]

    identity_number = _clean(national_id)
    if identity_number:
        row = conn.execute(
            "SELECT user_ID FROM USERS WHERE NationalID = ?", (identity_number,)
        ).fetchone()
        if row:
            return row["user_ID"]

    raise ValueError(
        "No registered user matches this claim. "
        "Send the logged-in user_id, or make sure the National ID on the invoice "
        "matches a registered member."
    )


def get_or_create_provider(conn, provider_name):
    """Providers ما فيه UNIQUE على الاسم، فنطابق بدون حساسية لحالة الأحرف."""
    name = _require(provider_name, "HospitalName")
    row = conn.execute(
        "SELECT ProviderID FROM Providers WHERE lower(ProviderName) = lower(?)", (name,)
    ).fetchone()
    if row:
        return row["ProviderID"]

    cursor = conn.execute(
        "INSERT INTO Providers (ProviderName, ProviderType) VALUES (?, ?)",
        (name, _provider_type(name)),
    )
    return cursor.lastrowid


def get_or_create_diagnosis(conn, diagnosis_code, diagnosis_description):
    """DiagnosisCode مفهرس UNIQUE، فنعيد استخدام التشخيص الموجود."""
    code = _require(diagnosis_code, "DiagnosisCode")
    row = conn.execute(
        "SELECT DiagnosisID FROM Diagnoses WHERE DiagnosisCode = ?", (code,)
    ).fetchone()
    if row:
        return row["DiagnosisID"]

    description = _require(diagnosis_description, "DiagnosisDescription")
    cursor = conn.execute(
        "INSERT INTO Diagnoses (DiagnosisCode, DiagnosisDescription) VALUES (?, ?)",
        (code, description),
    )
    return cursor.lastrowid


def insert_claim(conn, user_id, provider_id, diagnosis_id, claim):
    cursor = conn.execute(
        """
        INSERT INTO Claims (
            UserID, ProviderID, DiagnosisID,
            InvoiceNumber, InvoiceDate, DoctorName,
            TotalAmount, ClinicalSummary, ClaimStatus
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            provider_id,
            diagnosis_id,
            claim["InvoiceNumber"],
            claim["InvoiceDate"],
            claim["DoctorName"],
            claim["TotalAmount"],
            claim["ClinicalSummary"],
            claim["ClaimStatus"],
        ),
    )
    return cursor.lastrowid


def insert_document(conn, claim_id, document_type, file_name):
    """DocumentType فيه CHECK: Invoice / Medical Report / Prescription / Other."""
    conn.execute(
        "INSERT INTO Documents (ClaimID, DocumentType, FileName) VALUES (?, ?, ?)",
        (claim_id, document_type, file_name),
    )


def store_claim_document(claim_id, document_type, original_name, content_type, content):
    conn = get_connection()
    try:
        document = conn.execute(
            """SELECT DocumentID FROM Documents
               WHERE ClaimID = ? AND DocumentType = ?
               ORDER BY DocumentID DESC LIMIT 1""",
            (claim_id, document_type),
        ).fetchone()
        if document is None:
            raise LookupError(f"Document record for {document_type} was not found.")
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", Path(original_name or "document").name)
        stored_name = f"{document['DocumentID']}_{safe_name}"
        claim_dir = UPLOADS_DIR / str(claim_id)
        claim_dir.mkdir(parents=True, exist_ok=True)
        (claim_dir / stored_name).write_bytes(content)
        conn.execute(
            """INSERT OR REPLACE INTO ClaimDocumentFiles (DocumentID, StoredName, ContentType)
               VALUES (?, ?, ?)""",
            (document["DocumentID"], stored_name, content_type or "application/octet-stream"),
        )
        conn.commit()
    finally:
        conn.close()


def get_claim_document_file(claim_id, document_id):
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT d.FileName, f.StoredName, f.ContentType
               FROM Documents d JOIN ClaimDocumentFiles f ON f.DocumentID = d.DocumentID
               WHERE d.ClaimID = ? AND d.DocumentID = ?""",
            (claim_id, document_id),
        ).fetchone()
        if row is None:
            return None
        path = (UPLOADS_DIR / str(claim_id) / row["StoredName"]).resolve()
        if not path.is_file() or UPLOADS_DIR.resolve() not in path.parents:
            return None
        return {"path": path, "name": row["FileName"], "content_type": row["ContentType"]}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Persistence entry points
# ---------------------------------------------------------------------------

def save_claim_from_analysis(analysis, invoice_filename, report_filename, user_id=None):
    """يخزّن نتيجة تحليل الـ AI في الجداول الموجودة ويرجع ClaimID."""
    extracted = analysis.get("data") or {}
    clinical = analysis.get("clinical_analysis") or {}

    original_amount = _parse_amount(extracted.get("TotalAmount"))
    amount_sar, currency_code, exchange_rate = convert_to_sar(
        original_amount, extracted.get("Currency")
    )

    claim = {
        "InvoiceNumber": _require(extracted.get("InvoiceNumber"), "InvoiceNumber"),
        "InvoiceDate": _parse_date(extracted.get("InvoiceDate")),
        "DoctorName": _require(extracted.get("DoctorName"), "DoctorName"),
        "TotalAmount": amount_sar,
        "ClinicalSummary": _pack_clinical_summary(
            {
                # بيانات المستند اللي ما لها أعمدة في السكيمة
                "PatientName": _clean(extracted.get("PatientName")),
                "ClaimRef": _clean(extracted.get("ClaimId")),
                "MemberId": _clean(extracted.get("MemberId")),
                "DocumentNationalId": _clean(extracted.get("NationalId")),
                "ProviderName": _clean(extracted.get("ProviderName")),
                "Department": _clean(extracted.get("Department")),
                "ClaimType": _clean(extracted.get("ClaimType")),
                "InsuranceCompany": _clean(extracted.get("InsuranceCompany")),
                "PolicyNumber": _clean(extracted.get("PolicyNumber")),
                "ServiceDate": _clean(extracted.get("ServiceDate")),
                # المبلغ الأصلي قبل التحويل (نخزّنه فقط لو العملة مو ريال)
                "OriginalAmount": None if currency_code == "SAR" else original_amount,
                "OriginalCurrency": None if currency_code == "SAR" else currency_code,
                "ExchangeRate": None if currency_code == "SAR" else exchange_rate,
                # نتيجة تدقيق الـ AI: بدونها الفرونت ما يقدر يقول "المستندات مطابقة"
                "IsValid": analysis.get("is_valid") is not False,
                "MatchStatus": (_clean(analysis.get("match_status")) or "success").lower(),
                "ValidationMessage": _clean(analysis.get("validation_message")),
                "Discrepancies": analysis.get("discrepancies") or [],
                "CoverageHint": _clean(clinical.get("CoverageHint")),
                "Confidence": analysis.get("confidence"),
            },
            _clean(clinical.get("ClinicalSummary")),
        ),
        "ClaimStatus": _claim_status(analysis),
    }

    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT ClaimID FROM Claims WHERE InvoiceNumber = ?",
            (claim["InvoiceNumber"],),
        ).fetchone()
        if existing:
            raise DuplicateClaimError(claim["InvoiceNumber"], existing["ClaimID"])

        resolved_user_id = resolve_user_id(
            conn, user_id=user_id, national_id=extracted.get("NationalId")
        )
        provider_id = get_or_create_provider(conn, extracted.get("HospitalName"))
        diagnosis_id = get_or_create_diagnosis(
            conn, extracted.get("DiagnosisCode"), extracted.get("DiagnosisDescription")
        )

        claim_id = insert_claim(conn, resolved_user_id, provider_id, diagnosis_id, claim)

        if invoice_filename:
            insert_document(conn, claim_id, "Invoice", invoice_filename)
        if report_filename:
            insert_document(conn, claim_id, "Medical Report", report_filename)

        conn.commit()
        return claim_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


_CLAIM_SELECT = """
    SELECT
        c.ClaimID, c.InvoiceNumber, c.InvoiceDate, c.DoctorName,
        c.TotalAmount, c.ClinicalSummary, c.ClaimStatus, c.CreatedAt,
        u.user_ID AS UserID, u.name AS AccountHolderName,
        u.NationalID AS RegisteredNationalId,
        u.Email AS AccountHolderEmail, NULL AS AccountHolderPhone,
        p.ProviderName AS HospitalName, p.ProviderType, p.City,
        d.DiagnosisCode, d.DiagnosisDescription
    FROM Claims c
    JOIN USERS u ON u.user_ID = c.UserID
    JOIN Providers p ON p.ProviderID = c.ProviderID
    JOIN Diagnoses d ON d.DiagnosisID = c.DiagnosisID
"""


def _hydrate_claim(conn, row):
    """يحوّل صف قاعدة البيانات لقاموس كامل مع فك الـ meta وجلب المستندات."""
    result = dict(row)
    result["TotalAmount"] = float(result["TotalAmount"])

    meta, clinical_summary = _unpack_clinical_summary(result["ClinicalSummary"])
    result["ClinicalSummary"] = clinical_summary

    registered_national_id = result.pop("RegisteredNationalId")

    # بيانات المريض المذكورة في الفاتورة هي المرجع، ولو ناقصة نرجع لبيانات الحساب
    result["PatientName"] = meta.get("PatientName") or result["AccountHolderName"]
    result["NationalId"] = meta.get("DocumentNationalId") or registered_national_id
    result["ClaimRef"] = meta.get("ClaimRef")
    result["MemberId"] = meta.get("MemberId")
    result["ProviderName"] = meta.get("ProviderName")
    result["Department"] = meta.get("Department")
    result["ClaimType"] = meta.get("ClaimType")
    result["InsuranceCompany"] = meta.get("InsuranceCompany")
    result["PolicyNumber"] = meta.get("PolicyNumber")
    result["ServiceDate"] = meta.get("ServiceDate")
    result["Currency"] = "SAR"
    result["OriginalAmount"] = meta.get("OriginalAmount")
    result["OriginalCurrency"] = meta.get("OriginalCurrency")
    result["ExchangeRate"] = meta.get("ExchangeRate")

    result["Verification"] = {
        "IsValid": meta.get("IsValid", True),
        "MatchStatus": meta.get("MatchStatus", "success"),
        "ValidationMessage": meta.get("ValidationMessage"),
        "Discrepancies": meta.get("Discrepancies") or [],
        "CoverageHint": meta.get("CoverageHint"),
        "Confidence": meta.get("Confidence"),
    }

    documents = conn.execute(
        """
        SELECT d.DocumentID, d.DocumentType, d.FileName, d.UploadDate,
               CASE WHEN f.DocumentID IS NULL THEN 0 ELSE 1 END AS HasOriginal
        FROM Documents d
        LEFT JOIN ClaimDocumentFiles f ON f.DocumentID = d.DocumentID
        WHERE d.ClaimID = ?
        ORDER BY d.DocumentID
        """,
        (result["ClaimID"],),
    ).fetchall()
    result["Documents"] = [dict(document) for document in documents]

    return result


def get_claim_by_id(claim_id):
    """يرجع المطالبة المخزّنة مع بيانات المنشأة والتشخيص والمستندات، أو None."""
    conn = get_connection()
    try:
        row = conn.execute(
            _CLAIM_SELECT + " WHERE c.ClaimID = ?", (claim_id,)
        ).fetchone()
        if row is None:
            return None
        return _hydrate_claim(conn, row)
    finally:
        conn.close()


def list_claims():
    """يرجع كل المطالبات (الأحدث أولاً) بنفس شكل get_claim_by_id."""
    conn = get_connection()
    try:
        rows = conn.execute(
            _CLAIM_SELECT + " ORDER BY c.ClaimID DESC"
        ).fetchall()
        return [_hydrate_claim(conn, row) for row in rows]
    finally:
        conn.close()


def update_claim_status(claim_id, status):
    """يحدّث حالة المطالبة. القيم المسموحة من الـ CHECK constraint."""
    allowed = {"Pending", "Approved", "Rejected"}
    if status not in allowed:
        raise ValueError(f"Invalid status '{status}'. Allowed: {', '.join(sorted(allowed))}")

    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE Claims SET ClaimStatus = ? WHERE ClaimID = ?", (status, claim_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def add_claim_notification(claim_id, notification_type, title, message, customer_status=None):
    conn = get_connection()
    try:
        claim = conn.execute("SELECT UserID FROM Claims WHERE ClaimID = ?", (claim_id,)).fetchone()
        if claim is None:
            return False
        conn.execute(
            """INSERT INTO ClaimNotifications
               (ClaimID, UserID, NotificationType, Title, Message, CustomerStatus)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (claim_id, claim["UserID"], notification_type, title, message, customer_status),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def latest_customer_status(claim_id):
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT CustomerStatus FROM ClaimNotifications
               WHERE ClaimID = ? AND CustomerStatus IS NOT NULL
               ORDER BY NotificationID DESC LIMIT 1""",
            (claim_id,),
        ).fetchone()
        return row["CustomerStatus"] if row else None
    finally:
        conn.close()


def list_user_notifications(user_id):
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT n.*, c.ClinicalSummary FROM ClaimNotifications n
               JOIN Claims c ON c.ClaimID = n.ClaimID
               WHERE n.UserID = ? ORDER BY n.NotificationID DESC""",
            (user_id,),
        ).fetchall()
        notifications = []
        for row in rows:
            meta, _ = _unpack_clinical_summary(row["ClinicalSummary"])
            notifications.append({
                "id": row["NotificationID"],
                "claimId": meta.get("ClaimRef") or f"CLM-{row['ClaimID']:04d}",
                "claimDbId": row["ClaimID"],
                "sender": "Claims reviewer",
                "type": row["NotificationType"],
                "title": row["Title"],
                "preview": row["Message"],
                "timestamp": row["CreatedAt"],
                "unread": True,
                "thread": [{"from": "employee", "text": row["Message"], "time": row["CreatedAt"]}],
            })
        return notifications
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Employee view mapping
# ---------------------------------------------------------------------------

# الحالات اللي تفهمها واجهة الموظف (لها كلاسات CSS جاهزة)
_STATUS_MAP = {
    "Pending": "Pending Review",
    "Approved": "Completed",
    "Rejected": "Rejected",
}

_TIMELINE_BY_STATUS = {
    "Pending Review": "Employee Review",
    "Under Review": "Employee Review",
    "Missing Documents": "Waiting for Member",
    "Rejected": "Waiting for Member",
    "Completed": "Completed",
}


def _readiness(claim):
    """نسبة جاهزية المطالبة: تنقص مع كل ملاحظة تدقيق أو مستند ناقص."""
    score = 100
    for item in claim["Verification"]["Discrepancies"]:
        score -= 25 if str(item.get("severity", "low")).lower() == "high" else 8

    for field in ("ClaimRef", "MemberId", "NationalId", "PolicyNumber", "InsuranceCompany"):
        if not claim.get(field):
            score -= 5

    if len(claim["Documents"]) < 2:
        score -= 20

    return max(0, min(100, score))


def _missing_documents(claim):
    notes = []
    types = {document["DocumentType"] for document in claim["Documents"]}
    if "Invoice" not in types:
        notes.append("Invoice")
    if "Medical Report" not in types:
        notes.append("Medical Report")
    if not claim.get("PolicyNumber"):
        notes.append("Policy number on the invoice")
    if not claim.get("MemberId"):
        notes.append("Member ID on the invoice")
    return notes


def _verification_checklist(claim):
    """يبني قائمة التحقق اللي يعرضها AIVerificationChecklist."""
    verification = claim["Verification"]
    items = []

    types = {document["DocumentType"] for document in claim["Documents"]}
    items.append({
        "label": "Required documents uploaded",
        "state": "success" if {"Invoice", "Medical Report"} <= types else "error",
        "detail": "Both the invoice and the medical report were received."
        if {"Invoice", "Medical Report"} <= types
        else "One of the two required documents is missing.",
    })

    if verification["IsValid"] is False:
        items.append({
            "label": "Document type validation",
            "state": "error",
            "detail": verification["ValidationMessage"] or "The uploaded documents did not pass validation.",
        })
    else:
        items.append({
            "label": "Document type validation",
            "state": "success",
            "detail": "Image 1 was read as an invoice and image 2 as a medical report.",
        })

    match_status = verification["MatchStatus"]
    items.append({
        "label": "Invoice matches medical report",
        "state": "success" if match_status == "success" else "warning" if match_status == "warning" else "error",
        "detail": "All cross-checked fields are consistent across both documents."
        if match_status == "success"
        else f"{len(verification['Discrepancies'])} difference(s) were detected between the two documents.",
    })

    for item in verification["Discrepancies"]:
        severity = str(item.get("severity", "low")).lower()
        items.append({
            "label": f"Field check: {item.get('field', 'Unknown field')}",
            "state": "error" if severity == "high" else "warning",
            "detail": f"Invoice shows \"{item.get('invoice_value')}\" while the report shows "
                      f"\"{item.get('report_value')}\".",
        })

    items.append({
        "label": "Member identity on invoice",
        "state": "success" if claim.get("NationalId") and claim.get("MemberId") else "warning",
        "detail": f"National ID {claim.get('NationalId') or 'not found'} / Member ID "
                  f"{claim.get('MemberId') or 'not found'} were read from the invoice.",
    })

    items.append({
        "label": "Total amount extracted",
        "state": "success",
        "detail": f"Grand total including VAT: SAR {claim['TotalAmount']:.2f}.",
    })

    return items


def to_employee_claim(claim):
    """يحوّل المطالبة لشكل البيانات اللي تتوقعه صفحات الموظف."""
    verification = claim["Verification"]
    status = _STATUS_MAP.get(claim["ClaimStatus"], "Pending Review")

    workflow_status = latest_customer_status(claim["ClaimID"])
    if claim["ClaimStatus"] == "Pending" and workflow_status == "Action Required":
        status = "Waiting for Member"

    missing = _missing_documents(claim)
    if status == "Pending Review" and missing:
        status = "Missing Documents"

    high_severity = any(
        str(item.get("severity", "low")).lower() == "high"
        for item in verification["Discrepancies"]
    )
    priority = "High" if (high_severity or claim["TotalAmount"] >= 3000) else (
        "Medium" if verification["Discrepancies"] or claim["TotalAmount"] >= 1000 else "Low"
    )

    submission_date = (claim["CreatedAt"] or "")[:10]

    highlights = {}
    if claim.get("DiagnosisDescription"):
        highlights["Diagnosis"] = f"{claim['DiagnosisDescription']} ({claim.get('DiagnosisCode')})"
    if claim.get("Department"):
        highlights["Clinic / Department"] = claim["Department"]
    if claim.get("DoctorName"):
        highlights["Treating Physician"] = claim["DoctorName"]
    if claim.get("ProviderName"):
        highlights["Service Provider"] = claim["ProviderName"]
    highlights["Claimed Amount"] = f"SAR {claim['TotalAmount']:,.2f}"
    if claim.get("OriginalCurrency"):
        highlights["Original Amount"] = (
            f"{claim['OriginalCurrency']} {claim['OriginalAmount']:,.2f} "
            f"(converted at {claim['ExchangeRate']} SAR)"
        )
    if verification.get("CoverageHint"):
        highlights["Coverage Note"] = verification["CoverageHint"]

    return {
        "id": claim.get("ClaimRef") or f"CLM-{claim['ClaimID']:04d}",
        "claimDbId": claim["ClaimID"],
        "member": {
            "name": claim.get("PatientName"),
            "memberId": claim.get("MemberId") or "—",
            "nationalId": claim.get("NationalId") or "—",
            "policyNumber": claim.get("PolicyNumber") or "—",
            "phone": claim.get("AccountHolderPhone") or "—",
            "email": claim.get("AccountHolderEmail") or "—",
        },
        "submittedBy": claim.get("AccountHolderName"),
        "insuranceCompany": claim.get("InsuranceCompany") or "—",
        "claimType": claim.get("ClaimType") or "Reimbursement",
        "serviceType": claim.get("ProviderType") or "Outpatient",
        "submissionDate": submission_date,
        "invoiceDate": claim["InvoiceDate"],
        "invoiceNumber": claim["InvoiceNumber"],
        "provider": claim.get("HospitalName"),
        "department": claim.get("Department") or "—",
        "amount": claim["TotalAmount"],
        "currency": "SAR",
        "priority": priority,
        "status": status,
        "assignedTo": None,
        "readiness": _readiness(claim),
        "missingDocuments": missing,
        "potentialDuplicate": False,
        "aiConfidence": verification.get("Confidence") or 90,
        "aiSummary": claim.get("ClinicalSummary") or "No clinical summary was generated for this claim.",
        "highlights": highlights,
        "documents": [
            {
                "id": document["DocumentID"],
                "name": document["FileName"],
                "type": document["DocumentType"],
                "uploadDate": (document["UploadDate"] or "")[:10],
                "status": "Verified" if verification["MatchStatus"] == "success" else "Needs attention",
                "previewUrl": f"http://127.0.0.1:8001/api/employee/claims/{claim['ClaimID']}/documents/{document['DocumentID']}" if document.get("HasOriginal") else None,
            }
            for document in claim["Documents"]
        ],
        "verification": _verification_checklist(claim),
        "currentStage": _TIMELINE_BY_STATUS.get(status, "Employee Review"),
        "completionDate": submission_date if status == "Completed" else None,
    }


def list_employee_claims():
    return [to_employee_claim(claim) for claim in list_claims()]


def to_customer_claim(claim):
    raw_status = claim["ClaimStatus"]
    workflow_status = latest_customer_status(claim["ClaimID"])
    status = workflow_status if raw_status == "Pending" and workflow_status else {
        "Pending": "Under Review", "Approved": "Approved", "Rejected": "Rejected"
    }.get(raw_status, "Submitted")
    descriptions = {
        "Under Review": "A reviewer is checking your documents.",
        "Action Required": "We need additional information from you.",
        "Approved": "Your claim has been approved.",
        "Rejected": "Open the claim to view the decision reason.",
    }
    reference = claim.get("ClaimRef") or f"CLM-{claim['ClaimID']:04d}"
    submitted = (claim.get("CreatedAt") or "")[:10]
    return {
        "id": reference,
        "claimDbId": claim["ClaimID"],
        "submitted": submitted,
        "amount": f"SAR {claim['TotalAmount']:,.2f}",
        "status": status,
        "description": descriptions.get(status, "Your claim has been received."),
        "latestUpdate": f"Status updated: {status}",
        "category": claim.get("ClaimType") or "Medical reimbursement",
        "stage": 2 if status in {"Under Review", "Action Required"} else 3,
        "order": claim["ClaimID"],
        "documents": [document["FileName"] for document in claim["Documents"]],
        "timeline": [[submitted, "Claim submitted"], ["Latest", f"Claim status: {status}"]],
        "request": ({
            "title": "Additional information required",
            "message": "Your claims reviewer requested additional supporting documents. Open this claim to respond.",
            "date": "Latest update",
            "action": "Upload supporting documents",
        } if status == "Action Required" else None),
    }


def list_user_claims(user_id):
    conn = get_connection()
    try:
        rows = conn.execute(
            _CLAIM_SELECT + " WHERE c.UserID = ? ORDER BY c.ClaimID DESC", (user_id,)
        ).fetchall()
        return [to_customer_claim(_hydrate_claim(conn, row)) for row in rows]
    finally:
        conn.close()
