"""ملف المستفيد: الفئة التأمينية، العائلة، الموافقات، والتاريخ المرضي.

القاعدة الأساسية هنا: من بلغ 18 سنة له حق منع مشاركة بياناته مع رب الأسرة،
والنظام يحترم ذلك حتى لو كان رب الأسرة هو من يرفع المطالبة.
"""

from datetime import date, datetime

from database import get_connection
from policy_rules import DEFAULT_TIER, TIERS, classify_benefit

CONSENT_AGE = 18


# ---------------------------------------------------------------------------
# الفئة التأمينية
# ---------------------------------------------------------------------------

def get_member_policy(user_id):
    """يرجع الفئة والسقف السنوي للمستفيد."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT Tier, PolicyNumber, PolicyStart, PolicyEnd, InsuranceCompany "
            "FROM MemberPolicy WHERE user_ID = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

    tier = (row["Tier"] if row else DEFAULT_TIER) or DEFAULT_TIER
    if tier not in TIERS:
        tier = DEFAULT_TIER

    config = TIERS[tier]
    return {
        "tier": tier,
        "tier_label_ar": config["label_ar"],
        "annual_cap": config["annual_cap"],
        "benefit_multiplier": config["benefit_multiplier"],
        "room_type": config["room_type"],
        "policy_number": row["PolicyNumber"] if row else None,
        "policy_start": row["PolicyStart"] if row else None,
        "policy_end": row["PolicyEnd"] if row else None,
        "insurance_company": (row["InsuranceCompany"] if row else None) or "Bupa",
    }


def set_member_tier(user_id, tier):
    if tier not in TIERS:
        raise ValueError(f"Unknown tier '{tier}'. Allowed: {', '.join(TIERS)}")
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO MemberPolicy (user_ID, Tier) VALUES (?, ?) "
            "ON CONFLICT(user_ID) DO UPDATE SET Tier = excluded.Tier",
            (user_id, tier),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# استهلاك الحدود
# ---------------------------------------------------------------------------

def benefit_usage(user_id, benefit_code, year=None, exclude_claim_id=None):
    """كم استهلك المستفيد من هذا البند قبل المطالبة الحالية.

    استبعاد المطالبة الحالية ضروري، وإلا حُسبت على نفسها وظهر للموظف رقمان
    متناقضان: حد البند مستهلك 0 والسقف السنوي مستهلك بقيمة نفس المطالبة.
    """
    year = year or date.today().year
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(COALESCE(PayableAmount, TotalAmount)), 0) AS used
            FROM Claims
            WHERE UserID = ? AND BenefitCode = ?
              AND ClaimStatus IN ('Approved', 'Pending')
              AND strftime('%Y', COALESCE(InvoiceDate, CreatedAt)) = ?
              AND (? IS NULL OR ClaimID != ?)
            """,
            (user_id, benefit_code, str(year), exclude_claim_id, exclude_claim_id),
        ).fetchone()
        return float(row["used"] or 0)
    finally:
        conn.close()


def annual_usage(user_id, year=None, exclude_claim_id=None):
    """إجمالي ما استهلكه المستفيد من السقف السنوي قبل المطالبة الحالية."""
    year = year or date.today().year
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(COALESCE(PayableAmount, TotalAmount)), 0) AS used
            FROM Claims
            WHERE UserID = ? AND ClaimStatus IN ('Approved', 'Pending')
              AND strftime('%Y', COALESCE(InvoiceDate, CreatedAt)) = ?
              AND (? IS NULL OR ClaimID != ?)
            """,
            (user_id, str(year), exclude_claim_id, exclude_claim_id),
        ).fetchone()
        return float(row["used"] or 0)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# العائلة والموافقات
# ---------------------------------------------------------------------------

def _member_age(conn, user_id):
    row = conn.execute(
        "SELECT Age, DateOfBirth FROM Users WHERE user_ID = ?", (user_id,)
    ).fetchone()
    if row is None:
        return None
    if row["Age"] is not None:
        return int(row["Age"])
    if row["DateOfBirth"]:
        try:
            born = datetime.strptime(row["DateOfBirth"], "%Y-%m-%d").date()
            today = date.today()
            return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        except ValueError:
            return None
    return None


def get_consent(user_id):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT ShareWithHead, ShareHistory FROM DataSharingConsent WHERE user_ID = ?",
            (user_id,),
        ).fetchone()
        age = _member_age(conn, user_id)
    finally:
        conn.close()

    # القاصر لا يملك حق المنع نظاميًا، فولي الأمر يرى بياناته
    if age is not None and age < CONSENT_AGE:
        return {"age": age, "is_adult": False, "share_with_head": True, "share_history": True}

    if row is None:
        return {"age": age, "is_adult": True, "share_with_head": True, "share_history": True}

    return {
        "age": age,
        "is_adult": True,
        "share_with_head": bool(row["ShareWithHead"]),
        "share_history": bool(row["ShareHistory"]),
    }


def set_consent(user_id, share_with_head=None, share_history=None):
    """يحدّث موافقة المشاركة. البالغ فقط يستطيع المنع."""
    consent = get_consent(user_id)
    if not consent["is_adult"]:
        raise PermissionError(
            f"Members under {CONSENT_AGE} cannot change data-sharing settings."
        )

    conn = get_connection()
    try:
        current = conn.execute(
            "SELECT ShareWithHead, ShareHistory FROM DataSharingConsent WHERE user_ID = ?",
            (user_id,),
        ).fetchone()
        new_head = int(share_with_head if share_with_head is not None
                       else (current["ShareWithHead"] if current else 1))
        new_history = int(share_history if share_history is not None
                          else (current["ShareHistory"] if current else 1))
        conn.execute(
            "INSERT INTO DataSharingConsent (user_ID, ShareWithHead, ShareHistory, UpdatedAt) "
            "VALUES (?, ?, ?, CURRENT_TIMESTAMP) "
            "ON CONFLICT(user_ID) DO UPDATE SET ShareWithHead = excluded.ShareWithHead, "
            "ShareHistory = excluded.ShareHistory, UpdatedAt = CURRENT_TIMESTAMP",
            (user_id, new_head, new_history),
        )
        conn.commit()
    finally:
        conn.close()

    return get_consent(user_id)


def get_family(user_id):
    """يرجع رب الأسرة والأفراد، مع احترام موافقة كل بالغ."""
    conn = get_connection()
    try:
        head_row = conn.execute(
            """
            SELECT f.HeadUserID, u.Name, f.Relationship
            FROM FamilyLinks f JOIN Users u ON u.user_ID = f.HeadUserID
            WHERE f.MemberUserID = ?
            """,
            (user_id,),
        ).fetchone()

        member_rows = conn.execute(
            """
            SELECT f.MemberUserID, u.Name, u.Age, u.NationalID, f.Relationship
            FROM FamilyLinks f JOIN Users u ON u.user_ID = f.MemberUserID
            WHERE f.HeadUserID = ?
            ORDER BY f.LinkID
            """,
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    dependents = []
    for row in member_rows:
        consent = get_consent(row["MemberUserID"])
        dependents.append({
            "user_id": row["MemberUserID"],
            "name": row["Name"],
            "relationship": row["Relationship"],
            "age": row["Age"],
            # البيانات تُحجب لو البالغ رفض المشاركة
            "national_id": row["NationalID"] if consent["share_with_head"] else None,
            "shares_data": consent["share_with_head"],
            "shares_history": consent["share_history"],
            "is_adult": consent["is_adult"],
        })

    return {
        "is_head": bool(member_rows),
        "head": None if head_row is None else {
            "user_id": head_row["HeadUserID"],
            "name": head_row["Name"],
            "relationship": head_row["Relationship"],
        },
        "dependents": dependents,
    }


# ---------------------------------------------------------------------------
# التاريخ المرضي
# ---------------------------------------------------------------------------

def get_medical_history(user_id):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT ConditionCode, ConditionName, IsChronic, IsHereditary, DiagnosedOn, Notes "
            "FROM MedicalHistory WHERE user_ID = ? ORDER BY DiagnosedOn",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    return [{
        "code": row["ConditionCode"],
        "name": row["ConditionName"],
        "is_chronic": bool(row["IsChronic"]),
        "is_hereditary": bool(row["IsHereditary"]),
        "diagnosed_on": row["DiagnosedOn"],
        "notes": row["Notes"],
    } for row in rows]


def get_hereditary_context(user_id):
    """الأمراض الوراثية عند الوالدين التي قد تفسّر حالة الابن.

    تحترم موافقة كل والد: لو الوالد بالغ ومنع مشاركة تاريخه، لا يظهر.
    """
    conn = get_connection()
    try:
        parents = conn.execute(
            """
            SELECT f.HeadUserID AS parent_id, u.Name AS parent_name, f.Relationship
            FROM FamilyLinks f JOIN Users u ON u.user_ID = f.HeadUserID
            WHERE f.MemberUserID = ? AND f.Relationship IN ('Son','Daughter')
            """,
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    context = []
    for parent in parents:
        if not get_consent(parent["parent_id"])["share_history"]:
            continue
        for condition in get_medical_history(parent["parent_id"]):
            if condition["is_hereditary"]:
                context.append({
                    "relative": parent["parent_name"],
                    "relationship": "Parent",
                    **condition,
                })
    return context


def clinical_context_for_claim(user_id, diagnosis_code=None, procedure_code=None,
                               description=None, claim_type=None):
    """السياق الطبي الذي يظهر للموظف وقت مراجعة المطالبة.

    يجيب على سؤالين: هل الحالة مزمنة عند المريض؟ وهل لها أصل وراثي في العائلة؟
    """
    benefit_code, _ = classify_benefit(diagnosis_code, procedure_code, description, claim_type)
    code = (diagnosis_code or "").upper()

    own_history = get_medical_history(user_id)
    related_own = [
        item for item in own_history
        if code and (code.startswith(item["code"].upper()) or item["code"].upper().startswith(code[:3]))
    ]

    hereditary = get_hereditary_context(user_id)
    related_hereditary = [
        item for item in hereditary
        if code and (code.startswith(item["code"].upper()) or item["code"].upper().startswith(code[:3]))
    ]

    notes = []
    for item in related_own:
        if item["is_chronic"]:
            notes.append({
                "type": "chronic",
                "text_ar": f"المريض مشخّص بـ\"{item['name']}\" ({item['code']}) منذ "
                           f"{item['diagnosed_on']}، وهي حالة مزمنة. المطالبة الحالية امتداد "
                           f"لعلاج قائم وليست حالة جديدة.",
                "text_en": f"The member has been diagnosed with {item['name']} "
                           f"({item['code']}) since {item['diagnosed_on']} — a chronic "
                           f"condition. This claim continues existing treatment.",
            })

    for item in related_hereditary:
        notes.append({
            "type": "hereditary",
            "text_ar": f"{item['relative']} (أحد الوالدين) مصاب بـ\"{item['name']}\" "
                       f"({item['code']}) وهي حالة وراثية، مما يدعم الأصل الطبي للحالة "
                       f"لدى المستفيد.",
            "text_en": f"{item['relative']} (parent) has {item['name']} ({item['code']}), "
                       f"a hereditary condition, which supports the medical basis of this claim.",
        })

    return {
        "benefit_code": benefit_code,
        "has_chronic_match": bool([i for i in related_own if i["is_chronic"]]),
        "has_hereditary_match": bool(related_hereditary),
        "own_conditions": own_history,
        "related_own": related_own,
        "hereditary_context": hereditary,
        "notes": notes,
    }