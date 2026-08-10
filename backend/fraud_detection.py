"""نظام كشف الاحتيال.

ثلاث طبقات مستقلة:
  1. تحليل جنائي للمستند  — بصمة الملف، بيانات PDF الوصفية، آثار برامج التعديل
  2. سلوك المستفيد عبر الزمن — تكرار، تصاعد المبالغ، تركّز على مزوّد واحد
  3. القائمة السوداء       — قرار الموظف بعد التأكد

كل إشارة لها درجة، ومجموع الدرجات يحدد مستوى الخطورة.
"""

import hashlib
import io
import re
from collections import Counter
from datetime import date, datetime, timedelta

from database import get_connection

# برامج تحرير الصور والرسوميات: وجودها في منتج ملف "فاتورة" مؤشر قوي
_EDITING_SOFTWARE = re.compile(
    r"photoshop|illustrator|gimp|canva|inkscape|paint\.net|pixlr|affinity|figma|"
    r"acrobat\s*pro|pdfescape|foxit\s*phantom|nitro\s*pro|sejda|ilovepdf|smallpdf",
    re.IGNORECASE,
)

# أنظمة إصدار الفواتير المشروعة
# أنظمة إصدار الفواتير والتقارير المشروعة. القائمة واسعة عمدًا: المستشفيات
# تستخدم أنظمة لا حصر لها، ووسم كل نظام غير معروف كإشارة احتيال يغرق الموظف
# بتنبيهات لا قيمة لها.
_TRUSTED_PRODUCERS = re.compile(
    r"crystal\s*reports|jasper|sap|oracle|microsoft|wkhtmltopdf|reportlab|itext|"
    r"tcpdf|fpdf|prince|weasyprint|billing|invoic|emr|ehr|his\b|hospital|clinic|"
    r"medical|health|pharmac|lab\b|report|erp|epic|cerner|meditech|malaffi|nphies",
    re.IGNORECASE,
)

RISK_BANDS = ((70, "critical"), (45, "high"), (20, "medium"), (1, "low"))


def _band(score):
    for threshold, label in RISK_BANDS:
        if score >= threshold:
            return label
    return "clean"


def _signal(code, severity, score, detail_ar, detail_en):
    return {
        "code": code,
        "severity": severity,
        "score": score,
        "detail_ar": detail_ar,
        "detail_en": detail_en,
    }


# ---------------------------------------------------------------------------
# 1) التحليل الجنائي للمستند
# ---------------------------------------------------------------------------

def _average_hash(pdf_bytes):
    """بصمة إدراكية بسيطة (aHash 8x8) لأول صفحة — تكشف المستندات المتشابهة بصريًا."""
    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            if doc.page_count == 0:
                return None
            pixmap = doc[0].get_pixmap(matrix=fitz.Matrix(0.25, 0.25), colorspace=fitz.csGRAY)
            width, height = pixmap.width, pixmap.height
            if width < 8 or height < 8:
                return None
            samples = pixmap.samples
            cells = []
            for row in range(8):
                for col in range(8):
                    x = int(col * width / 8)
                    y = int(row * height / 8)
                    cells.append(samples[y * pixmap.stride + x])
            mean = sum(cells) / len(cells)
            bits = "".join("1" if value > mean else "0" for value in cells)
            return f"{int(bits, 2):016x}"
        finally:
            doc.close()
    except Exception:
        return None


def fingerprint_document(content, filename=None, content_type=None):
    """يستخرج بصمة الملف وبياناته الوصفية."""
    info = {
        "sha256": hashlib.sha256(content).hexdigest(),
        "file_size": len(content),
        "file_name": filename,
        "perceptual_hash": None,
        "producer": None,
        "creator": None,
        "created": None,
        "modified": None,
        "page_count": None,
    }

    if content[:5] != b"%PDF-":
        return info

    try:
        import fitz
        doc = fitz.open(stream=content, filetype="pdf")
        try:
            metadata = doc.metadata or {}
            info["producer"] = metadata.get("producer")
            info["creator"] = metadata.get("creator")
            info["created"] = metadata.get("creationDate")
            info["modified"] = metadata.get("modDate")
            info["page_count"] = doc.page_count
        finally:
            doc.close()
        info["perceptual_hash"] = _average_hash(content)
    except Exception:
        pass

    return info


def _hamming(hex_a, hex_b):
    if not hex_a or not hex_b:
        return None
    try:
        return bin(int(hex_a, 16) ^ int(hex_b, 16)).count("1")
    except ValueError:
        return None


def analyze_document(fingerprint, user_id=None, document_type="Invoice"):
    """يفحص مستندًا واحدًا ويرجع إشارات الاحتيال.

    يُستدعى قبل حفظ بصمة المطالبة الجارية، فلا خطر من مطابقتها لنفسها.
    """
    signals = []
    label = "الفاتورة" if document_type == "Invoice" else "التقرير الطبي"

    # Producer و Creator غالبًا متطابقان، فالدمج المباشر كان يكرّر الاسم في الرسالة
    parts = [p for p in (fingerprint.get("producer"), fingerprint.get("creator")) if p]
    producer = " / ".join(dict.fromkeys(parts))

    if producer and _EDITING_SOFTWARE.search(producer):
        matched = _EDITING_SOFTWARE.search(producer).group(0)
        signals.append(_signal(
            "EDITING_SOFTWARE", "high", 35,
            f"{label} أُنتجت ببرنامج تحرير رسوميات ({matched}) وليس بنظام فوترة. "
            "الفواتير النظامية تصدر من أنظمة المنشآت الطبية.",
            f"The {document_type.lower()} was produced by graphics-editing software "
            f"({matched}) rather than a billing system.",
        ))
    elif producer and not _TRUSTED_PRODUCERS.search(producer):
        signals.append(_signal(
            "UNKNOWN_PRODUCER", "low", 2,
            f"منتج {label} غير معروف: \"{producer[:60]}\".",
            f"The {document_type.lower()} was produced by \"{producer[:60]}\", which is "
            "not a recognised billing or clinical system. On its own this is weak "
            "evidence — many providers use in-house software.",
        ))

    # تعديل الملف بعد إنشائه بفارق زمني كبير
    created, modified = fingerprint.get("created"), fingerprint.get("modified")
    if created and modified and created != modified:
        try:
            parse = lambda v: datetime.strptime(v[2:16], "%Y%m%d%H%M%S")
            gap = (parse(modified) - parse(created)).total_seconds()
            if gap > 3600:
                hours = gap / 3600
                signals.append(_signal(
                    "POST_EDIT", "medium", 20,
                    f"{label} عُدّلت بعد {hours:,.1f} ساعة من إنشائها. الفواتير الأصلية "
                    "لا تُعدّل بعد إصدارها.",
                    f"The {document_type.lower()} was modified {hours:,.1f} hours after "
                    "creation. Original invoices are not edited after issuance.",
                ))
        except (ValueError, TypeError):
            pass

    if not producer and fingerprint.get("page_count"):
        signals.append(_signal(
            "STRIPPED_METADATA", "medium", 15,
            f"{label} بلا أي بيانات وصفية — قد تكون أُعيد إنشاؤها لإخفاء مصدرها.",
            f"The {document_type.lower()} has no metadata at all, which can indicate "
            "it was re-generated to hide its origin.",
        ))

    # مطابقة البصمة مع مستندات سابقة
    conn = get_connection()
    try:
        # الربط بـ Claims يستبعد بصمات المطالبات المحذوفة، وإلا أشار النظام
        # إلى مطالبة لم تعد موجودة ("مطابق للمطالبة #8" و#8 محذوفة).
        exact = conn.execute(
            """
            SELECT f.ClaimID, f.user_ID, f.FileName
            FROM DocumentFingerprints f
            JOIN Claims c ON c.ClaimID = f.ClaimID
            WHERE f.Sha256 = ?
            ORDER BY f.FingerprintID LIMIT 1
            """,
            (fingerprint["sha256"],),
        ).fetchone()

        if exact:
            same_member = user_id is not None and exact["user_ID"] == user_id
            signals.append(_signal(
                "REUSED_DOCUMENT", "critical", 60,
                f"نفس {label} بالضبط (بصمة متطابقة) مُستخدمة في المطالبة رقم "
                f"#{exact['ClaimID']}" + ("" if same_member else " لمستفيد آخر") + ".",
                f"The identical {document_type.lower()} was already used in claim "
                f"#{exact['ClaimID']}" + ("" if same_member else " by a different member") + ".",
            ))
        elif fingerprint.get("perceptual_hash"):
            candidates = conn.execute(
                """
                SELECT f.ClaimID, f.PerceptualHash
                FROM DocumentFingerprints f
                JOIN Claims c ON c.ClaimID = f.ClaimID
                WHERE f.PerceptualHash IS NOT NULL AND f.DocumentType = ?
                ORDER BY f.FingerprintID DESC LIMIT 400
                """,
                (document_type,),
            ).fetchall()
            for row in candidates:
                distance = _hamming(fingerprint["perceptual_hash"], row["PerceptualHash"])
                if distance is not None and distance <= 5:
                    signals.append(_signal(
                        "NEAR_DUPLICATE", "high", 40,
                        f"{label} تكاد تطابق مستند المطالبة #{row['ClaimID']} بصريًا "
                        f"(فرق {distance} بت فقط) — قد تكون نسخة معدّلة منها.",
                        f"The {document_type.lower()} is visually almost identical to the "
                        f"document in claim #{row['ClaimID']} (only {distance} bits differ), "
                        "suggesting an edited copy.",
                    ))
                    break
    finally:
        conn.close()

    return signals


def save_fingerprint(claim_id, user_id, document_type, fingerprint):
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO DocumentFingerprints
                (ClaimID, user_ID, DocumentType, FileName, Sha256, PerceptualHash,
                 FileSize, PdfProducer, PdfCreator, PdfCreated, PdfModified)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (claim_id, user_id, document_type, fingerprint.get("file_name"),
             fingerprint["sha256"], fingerprint.get("perceptual_hash"),
             fingerprint.get("file_size"), fingerprint.get("producer"),
             fingerprint.get("creator"), fingerprint.get("created"),
             fingerprint.get("modified")),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 2) سلوك المستفيد عبر الزمن
# ---------------------------------------------------------------------------

def member_history_signals(user_id, amount=None, provider_name=None, diagnosis_code=None):
    """يفحص سجل المستفيد بحثًا عن أنماط مشبوهة متكررة."""
    signals = []
    conn = get_connection()
    try:
        claims = conn.execute(
            """
            SELECT c.ClaimID, c.TotalAmount, c.InvoiceDate, c.CreatedAt, c.ClaimStatus,
                   c.FraudScore, p.ProviderName, d.DiagnosisCode
            FROM Claims c
            LEFT JOIN Providers p ON p.ProviderID = c.ProviderID
            LEFT JOIN Diagnoses d ON d.DiagnosisID = c.DiagnosisID
            WHERE c.UserID = ?
            ORDER BY c.ClaimID DESC
            """,
            (user_id,),
        ).fetchall()

        prior_flags = conn.execute(
            """
            SELECT COUNT(DISTINCT s.ClaimID) AS flagged
            FROM FraudSignals s
            JOIN Claims c ON c.ClaimID = s.ClaimID
            WHERE s.user_ID = ? AND s.Severity IN ('high','critical')
            """,
            (user_id,),
        ).fetchone()["flagged"]
    finally:
        conn.close()

    if not claims:
        return signals

    today = date.today()

    def parse(value):
        try:
            return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

    recent = [c for c in claims if (parse(c["CreatedAt"]) or today) >= today - timedelta(days=30)]
    if len(recent) >= 4:
        signals.append(_signal(
            "HIGH_FREQUENCY", "medium", 20,
            f"المستفيد قدّم {len(recent)} مطالبات خلال 30 يومًا — معدّل أعلى بكثير من المعتاد.",
            f"The member filed {len(recent)} claims in the last 30 days, well above "
            "the normal rate.",
        ))

    if prior_flags >= 2:
        signals.append(_signal(
            "REPEAT_OFFENDER", "critical", 55,
            f"المستفيد لديه {prior_flags} مطالبات سابقة حملت إشارات احتيال عالية الخطورة. "
            "هذا نمط متكرر وليس حادثة منفردة.",
            f"The member has {prior_flags} previous claims flagged with high-severity "
            "fraud signals — a repeated pattern, not an isolated incident.",
        ))
    elif prior_flags == 1:
        signals.append(_signal(
            "PRIOR_FLAG", "medium", 18,
            "للمستفيد مطالبة سابقة واحدة حملت إشارة احتيال عالية الخطورة.",
            "The member has one previous claim flagged for high-severity fraud signals.",
        ))

    rejected = [c for c in claims if c["ClaimStatus"] == "Rejected"]
    if len(claims) >= 3 and len(rejected) / len(claims) >= 0.5:
        signals.append(_signal(
            "HIGH_REJECTION_RATE", "high", 30,
            f"{len(rejected)} من أصل {len(claims)} من مطالبات المستفيد سبق رفضها "
            f"({len(rejected)/len(claims):.0%}).",
            f"{len(rejected)} of the member's {len(claims)} claims were previously "
            f"rejected ({len(rejected)/len(claims):.0%}).",
        ))

    if provider_name and len(claims) >= 3:
        providers = Counter(c["ProviderName"] for c in claims if c["ProviderName"])
        if providers and providers.most_common(1)[0][0] == provider_name:
            count, total = providers[provider_name], sum(providers.values())
            if count / total >= 0.8 and count >= 3:
                signals.append(_signal(
                    "PROVIDER_CONCENTRATION", "medium", 18,
                    f"{count} من أصل {total} من مطالبات المستفيد من نفس المنشأة "
                    f"\"{provider_name}\" — تركّز غير معتاد قد يشير لتواطؤ.",
                    f"{count} of the member's {total} claims come from the same provider "
                    f"\"{provider_name}\" — unusual concentration that can indicate collusion.",
                ))

    if amount is not None:
        amounts = [float(c["TotalAmount"] or 0) for c in claims if c["TotalAmount"]]
        if len(amounts) >= 3:
            average = sum(amounts) / len(amounts)
            if average > 0 and amount > average * 4:
                signals.append(_signal(
                    "AMOUNT_ESCALATION", "high", 28,
                    f"المبلغ {amount:,.2f} ريال يعادل {amount/average:.1f} ضعف متوسط "
                    f"مطالبات المستفيد السابقة ({average:,.2f} ريال).",
                    f"SAR {amount:,.2f} is {amount/average:.1f}x the member's average "
                    f"previous claim (SAR {average:,.2f}).",
                ))

    if diagnosis_code:
        same_diagnosis = [
            c for c in claims
            if c["DiagnosisCode"] and str(c["DiagnosisCode"]).upper() == str(diagnosis_code).upper()
            and (parse(c["InvoiceDate"]) or today) >= today - timedelta(days=90)
        ]
        if len(same_diagnosis) >= 3:
            signals.append(_signal(
                "REPEATED_DIAGNOSIS", "medium", 15,
                f"{len(same_diagnosis)} مطالبات بنفس التشخيص ({diagnosis_code}) خلال "
                "90 يومًا من منشآت أو تواريخ مختلفة.",
                f"{len(same_diagnosis)} claims with the same diagnosis ({diagnosis_code}) "
                "within 90 days.",
            ))

    return signals


# ---------------------------------------------------------------------------
# 3) القائمة السوداء
# ---------------------------------------------------------------------------

def is_blacklisted(user_id=None, national_id=None):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT Reason, AddedBy, AddedAt FROM Blacklist "
            "WHERE IsActive = 1 AND ((user_ID IS NOT NULL AND user_ID = ?) "
            "OR (NationalID IS NOT NULL AND NationalID = ?)) LIMIT 1",
            (user_id, national_id),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def add_to_blacklist(user_id=None, national_id=None, reason="", added_by="system"):
    if not user_id and not national_id:
        raise ValueError("Blacklist entry needs a user_id or a national_id.")
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO Blacklist (user_ID, NationalID, Reason, AddedBy) VALUES (?,?,?,?)",
            (user_id, national_id, reason, added_by),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def remove_from_blacklist(entry_id):
    conn = get_connection()
    try:
        conn.execute("UPDATE Blacklist SET IsActive = 0 WHERE EntryID = ?", (entry_id,))
        conn.commit()
    finally:
        conn.close()


def list_blacklist():
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT b.EntryID, b.user_ID, b.NationalID, b.Reason, b.AddedBy, b.AddedAt,
                   u.Name
            FROM Blacklist b LEFT JOIN Users u ON u.user_ID = b.user_ID
            WHERE b.IsActive = 1 ORDER BY b.AddedAt DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# التجميع
# ---------------------------------------------------------------------------

def scan_claim(user_id, invoice_fingerprint=None, report_fingerprint=None,
               amount=None, provider_name=None, diagnosis_code=None,
               national_id=None, policy_anomaly=None):
    """الفحص الكامل: مستندات + سلوك + قائمة سوداء + شذوذ المبلغ."""
    signals = []

    blacklist_entry = is_blacklisted(user_id=user_id, national_id=national_id)
    if blacklist_entry:
        signals.append(_signal(
            "BLACKLISTED", "critical", 100,
            f"المستفيد مُدرج في القائمة السوداء. السبب: {blacklist_entry['Reason']}",
            f"The member is on the blacklist. Reason: {blacklist_entry['Reason']}",
        ))

    if invoice_fingerprint:
        signals += analyze_document(invoice_fingerprint, user_id, "Invoice")
    if report_fingerprint:
        signals += analyze_document(report_fingerprint, user_id, "Medical Report")

    signals += member_history_signals(user_id, amount, provider_name, diagnosis_code)

    if policy_anomaly:
        severity = policy_anomaly["severity"]
        signals.append(_signal(
            "POLICY_AMOUNT_ANOMALY", severity,
            {"critical": 45, "high": 30, "medium": 12}.get(severity, 8),
            policy_anomaly["message_ar"], policy_anomaly["message_en"],
        ))

    score = min(100, sum(signal["score"] for signal in signals))
    risk = _band(score)

    return {
        "score": score,
        "risk_level": risk,
        "signals": sorted(signals, key=lambda s: -s["score"]),
        "blacklisted": blacklist_entry is not None,
        "recommendation": (
            "reject_and_blacklist" if risk == "critical"
            else "manual_investigation" if risk == "high"
            else "review" if risk == "medium"
            else "proceed"
        ),
    }


def save_signals(claim_id, user_id, signals):
    if not signals:
        return
    conn = get_connection()
    try:
        conn.executemany(
            "INSERT INTO FraudSignals (ClaimID, user_ID, Code, Severity, Score, Detail) "
            "VALUES (?,?,?,?,?,?)",
            [(claim_id, user_id, s["code"], s["severity"], s["score"], s["detail_en"])
             for s in signals],
        )
        conn.commit()
    finally:
        conn.close()