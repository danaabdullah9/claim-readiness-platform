"""قواعد قبول المطالبة قبل حفظها.

الفكرة: أي مطالبة ترسب في القواعد هنا لا تُحفظ في قاعدة البيانات إطلاقًا ولا
يوصل صاحبها لصفحة الملخص. الرفض يرجع للواجهة كقائمة أسباب مفهومة.
"""

import re
import unicodedata
from datetime import date, datetime
from difflib import SequenceMatcher

from database import _clean, _parse_date, get_connection

# مدة تقديم المطالبة القصوى من تاريخ الخدمة
CLAIM_WINDOW_DAYS = 90

# نسبة التشابه اللي نعتبر عندها الاسمين لنفس الشخص باختلاف إملائي فقط
# (Khalid Sultan / Khaled Soltan) بدل ما نرفضها كأسماء مختلفة.
NAME_MATCH_THRESHOLD = 0.85

_TITLES = {"mr", "mrs", "ms", "miss", "dr", "prof", "eng", "sheikh", "السيد", "السيدة", "الدكتور", "د"}

_ARABIC_DIACRITICS = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")


# ---------------------------------------------------------------------------
# مطابقة الأسماء
# ---------------------------------------------------------------------------

def _transliteration_key(token):
    """يوحّد اختلافات كتابة الأسماء العربية بالإنجليزي.

    Ahmed/Ahmad، Ali/Aly، Khalid/Khaled، Sultan/Soltan، Mohammed/Mohamed
    كلها تصير مفتاحًا واحدًا، لأن هذي الفروق إملائية مو أشخاص مختلفين.
    """
    text = token
    text = re.sub(r"(.)\1+", r"\1", text)          # الحروف المضاعفة: mm -> m
    text = text.replace("ph", "f").replace("ck", "k")
    text = re.sub(r"[eé]", "a", text)               # Ahmed -> Ahmad
    text = re.sub(r"[yj]", "i", text)               # Aly -> Ali
    text = re.sub(r"[ou]", "u", text)               # Soltan -> Sultan
    text = re.sub(r"h$", "", text)                  # Abdullah -> Abdulla
    text = re.sub(r"(.)\1+", r"\1", text)          # تكرار نتج عن الاستبدال
    return text


def _normalize_name(value):
    """يرجع قائمة كلمات الاسم بعد التوحيد الكامل (عربي وإنجليزي)."""
    text = unicodedata.normalize("NFKD", str(value or "")).lower()
    text = _ARABIC_DIACRITICS.sub("", text)
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    text = re.sub(r"[^0-9a-z\u0600-\u06FF\s]", " ", text)

    tokens = [token for token in text.split() if token and token not in _TITLES]
    return [_transliteration_key(token) for token in tokens]


def name_similarity(first, second):
    """نسبة 0-1 لتطابق الاسمين.

    نقارن من الاسم الأقصر إلى الأطول لأن الحساب غالبًا يحمل اسمًا ثنائيًا
    ("Ahmed Ali") بينما الفاتورة تحمل الاسم الرباعي الكامل، وهما نفس الشخص.
    """
    tokens_a = _normalize_name(first)
    tokens_b = _normalize_name(second)
    if not tokens_a or not tokens_b:
        return 0.0

    shorter, longer = (tokens_a, tokens_b) if len(tokens_a) <= len(tokens_b) else (tokens_b, tokens_a)

    # الاسم الأول لازم يطابق: "Ahmed Ali" و "Sara Ahmed" مو نفس الشخص
    first_name_score = SequenceMatcher(None, shorter[0], longer[0]).ratio()
    if first_name_score < 0.8:
        return min(first_name_score, 0.5)

    scores = [
        max(SequenceMatcher(None, token, other).ratio() for other in longer)
        for token in shorter
    ]
    return sum(scores) / len(scores)


def names_match(first, second):
    return name_similarity(first, second) >= NAME_MATCH_THRESHOLD


# ---------------------------------------------------------------------------
# مساعدات
# ---------------------------------------------------------------------------

def _rejection(code, title, detail):
    return {"code": code, "title": title, "detail": detail}


def _safe_date(value):
    try:
        return datetime.strptime(_parse_date(value), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _account_holder_name(user_id):
    if user_id is None:
        return None
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT name FROM USERS WHERE user_ID = ?", (user_id,)
        ).fetchone()
        return row["name"] if row else None
    finally:
        conn.close()


def _existing_claim(invoice_number):
    if not invoice_number:
        return None
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT ClaimID, InvoiceDate FROM Claims WHERE InvoiceNumber = ?",
            (invoice_number,),
        ).fetchone()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# القواعد
# ---------------------------------------------------------------------------

def _check_document_types(analysis, rejections):
    """المستندات نفسها: فاتورة حقيقية + تقرير طبي حقيقي."""
    if analysis.get("is_valid") is False:
        rejections.append(_rejection(
            "INVALID_DOCUMENTS",
            "The uploaded documents did not pass validation",
            analysis.get("validation_message")
            or "One of the two files is not the document type it should be.",
        ))


def _check_documents_related(analysis, extracted, rejections):
    """الفاتورة والتقرير لازم يكونان لنفس الحالة الطبية."""
    relation = analysis.get("document_relation") or {}

    invoice_code = (_clean(extracted.get("DiagnosisCode")) or "").upper()
    report_code = (_clean(extracted.get("ReportDiagnosisCode")) or "").upper()

    # فحص حاسم: أول حرف من كود ICD-10 يحدد فصل التشخيص. K = الفم والجهاز
    # الهضمي، H = العين والأذن. اختلافه يعني مستندين لحالتين مختلفتين.
    if invoice_code and report_code and invoice_code[0] != report_code[0]:
        rejections.append(_rejection(
            "UNRELATED_DOCUMENTS",
            "The invoice and the medical report are for different conditions",
            f"The invoice is billed under diagnosis {invoice_code} while the medical "
            f"report documents diagnosis {report_code}. Both documents must cover the "
            "same treatment.",
        ))
        return

    if relation.get("same_clinical_case") is False:
        invoice_area = _clean(relation.get("invoice_specialty")) or "the billed service"
        report_area = _clean(relation.get("report_specialty")) or "the reported condition"
        rejections.append(_rejection(
            "UNRELATED_DOCUMENTS",
            "The invoice and the medical report are for different conditions",
            _clean(relation.get("reason"))
            or f"The invoice covers {invoice_area} while the report covers {report_area}.",
        ))


def _check_patient_identity(extracted, account_holder_name, rejections):
    """اسم المريض في المستندين لازم يطابق اسم صاحب الحساب (فروق الإملاء مقبولة)."""
    invoice_name = _clean(extracted.get("PatientName"))
    report_name = _clean(extracted.get("ReportPatientName")) or invoice_name

    if invoice_name and report_name and not names_match(invoice_name, report_name):
        rejections.append(_rejection(
            "PATIENT_MISMATCH",
            "The invoice and the medical report name two different patients",
            f"The invoice is issued to \"{invoice_name}\" while the medical report is "
            f"for \"{report_name}\".",
        ))
        return

    if not account_holder_name or not invoice_name:
        return

    if not names_match(invoice_name, account_holder_name):
        rejections.append(_rejection(
            "NAME_MISMATCH",
            "The patient name does not match your account",
            f"The documents are issued to \"{invoice_name}\" but this account is "
            f"registered under \"{account_holder_name}\". A claim can only be submitted "
            "for the account holder.",
        ))


def _check_submission_window(extracted, rejections):
    """مهلة 90 يومًا من تاريخ الخدمة."""
    service_date = _safe_date(extracted.get("ServiceDate")) or _safe_date(extracted.get("InvoiceDate"))
    if service_date is None:
        return

    today = date.today()
    if service_date > today:
        rejections.append(_rejection(
            "FUTURE_DATE",
            "The service date is in the future",
            f"The documents are dated {service_date.isoformat()}, which is after today "
            f"({today.isoformat()}).",
        ))
        return

    age_in_days = (today - service_date).days
    if age_in_days > CLAIM_WINDOW_DAYS:
        rejections.append(_rejection(
            "LATE_SUBMISSION",
            f"The {CLAIM_WINDOW_DAYS}-day submission window has closed",
            f"The service was provided on {service_date.isoformat()}, which is "
            f"{age_in_days} days ago. Claims must be submitted within "
            f"{CLAIM_WINDOW_DAYS} days, so the deadline passed "
            f"{age_in_days - CLAIM_WINDOW_DAYS} day(s) ago.",
        ))


def _check_duplicate(extracted, rejections):
    """نفس الفاتورة ما تُرفع مرتين."""
    invoice_number = _clean(extracted.get("InvoiceNumber"))
    existing = _existing_claim(invoice_number)
    if existing:
        rejections.append(_rejection(
            "DUPLICATE_CLAIM",
            "This invoice has already been submitted",
            f"Invoice {invoice_number} was already submitted as claim "
            f"#{existing['ClaimID']}. A duplicate claim cannot be created.",
        ))


def _check_cross_validation(analysis, rejections):
    """التعارضات الجسيمة بين الفاتورة والتقرير (غير الاسم، له قاعدة خاصة)."""
    for item in analysis.get("discrepancies") or []:
        if str(item.get("severity", "low")).lower() != "high":
            continue
        field = str(item.get("field") or "").lower()
        if "name" in field:  # الاسم يُعالج في _check_patient_identity بمنطق التشابه
            continue
        rejections.append(_rejection(
            "FIELD_MISMATCH",
            f"The two documents disagree on {item.get('field')}",
            f"The invoice shows \"{item.get('invoice_value')}\" while the medical report "
            f"shows \"{item.get('report_value')}\".",
        ))


# ---------------------------------------------------------------------------
# نقطة الدخول
# ---------------------------------------------------------------------------

def validate_claim(analysis, user_id=None):
    """يرجع {"eligible": bool, "rejections": [...]}.

    تُستدعى بعد تحليل الـ AI وقبل الحفظ. لو eligible=False ما تُحفظ المطالبة
    ولا يُسمح للعميل بالانتقال لصفحة الملخص.
    """
    extracted = analysis.get("data") or {}
    rejections = []

    _check_document_types(analysis, rejections)
    _check_documents_related(analysis, extracted, rejections)
    _check_patient_identity(extracted, _account_holder_name(user_id), rejections)
    _check_submission_window(extracted, rejections)
    _check_duplicate(extracted, rejections)
    _check_cross_validation(analysis, rejections)

    # إزالة التكرار مع الحفاظ على الترتيب
    unique = []
    seen = set()
    for rejection in rejections:
        key = (rejection["code"], rejection["detail"])
        if key not in seen:
            seen.add(key)
            unique.append(rejection)

    return {"eligible": not unique, "rejections": unique}