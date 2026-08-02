import re
import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "claimDB.db"

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


class DuplicateClaimError(Exception):
    """المطالبة موجودة مسبقًا (InvoiceNumber مفهرس UNIQUE في قاعدة البيانات)."""

    def __init__(self, invoice_number, claim_id):
        super().__init__(f"Claim for invoice '{invoice_number}' already exists.")
        self.invoice_number = invoice_number
        self.claim_id = claim_id


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
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
    """يشيل رمز العملة والفواصل ويرجع رقم عشري."""
    text = _require(value, field_name)
    digits = re.sub(r"[^\d.\-]", "", text.replace(",", ""))
    try:
        return round(float(digits), 2)
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
            "SELECT user_ID FROM USERS WHERE identity_number = ?", (identity_number,)
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


# ---------------------------------------------------------------------------
# Persistence entry points
# ---------------------------------------------------------------------------

def save_claim_from_analysis(analysis, invoice_filename, report_filename, user_id=None):
    """يخزّن نتيجة تحليل الـ AI في الجداول الموجودة ويرجع ClaimID."""
    extracted = analysis.get("data") or {}
    clinical = analysis.get("clinical_analysis") or {}

    claim = {
        "InvoiceNumber": _require(extracted.get("InvoiceNumber"), "InvoiceNumber"),
        "InvoiceDate": _parse_date(extracted.get("InvoiceDate")),
        "DoctorName": _require(extracted.get("DoctorName"), "DoctorName"),
        "TotalAmount": _parse_amount(extracted.get("TotalAmount")),
        "ClinicalSummary": _clean(clinical.get("ClinicalSummary")),
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


def get_claim_by_id(claim_id):
    """يرجع المطالبة المخزّنة مع بيانات المنشأة والتشخيص والمستندات، أو None."""
    conn = get_connection()
    try:
        claim = conn.execute(
            """
            SELECT
                c.ClaimID, c.InvoiceNumber, c.InvoiceDate, c.DoctorName,
                c.TotalAmount, c.ClinicalSummary, c.ClaimStatus, c.CreatedAt,
                u.user_ID AS UserID, u.name AS PatientName,
                u.identity_number AS NationalId,
                p.ProviderName AS HospitalName, p.ProviderType, p.City,
                d.DiagnosisCode, d.DiagnosisDescription
            FROM Claims c
            JOIN USERS u ON u.user_ID = c.UserID
            JOIN Providers p ON p.ProviderID = c.ProviderID
            JOIN Diagnoses d ON d.DiagnosisID = c.DiagnosisID
            WHERE c.ClaimID = ?
            """,
            (claim_id,),
        ).fetchone()

        if claim is None:
            return None

        documents = conn.execute(
            """
            SELECT DocumentID, DocumentType, FileName, UploadDate
            FROM Documents
            WHERE ClaimID = ?
            ORDER BY DocumentID
            """,
            (claim_id,),
        ).fetchall()

        result = dict(claim)
        result["TotalAmount"] = float(result["TotalAmount"])
        result["Documents"] = [dict(document) for document in documents]
        return result
    finally:
        conn.close()
