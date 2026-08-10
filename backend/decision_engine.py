"""أتمتة المطالبات البسيطة ومحرّك القرار الموحّد.

الأتمتة تعالج المطالبات الروتينية بدون تدخل الموظف، بشروط صارمة: مبلغ صغير،
بند واضح، لا إشارات احتيال، والمستفيد ضمن حدوده. أي شك يذهب للموظف.
"""

from datetime import date, datetime, timedelta

from database import get_connection
from member_profile import (
    annual_usage,
    benefit_usage,
    clinical_context_for_claim,
    get_member_policy,
)
from policy_rules import BENEFITS, classify_benefit, evaluate_claim


# ---------------------------------------------------------------------------
# قواعد الأتمتة
# ---------------------------------------------------------------------------
# كل قاعدة: سقف المبلغ + البنود المسموحة + شرط إضافي اختياري

AUTOMATION_RULES = {
    "SIMPLE_CONSULTATION": {
        "name_ar": "كشفية عيادة بسيطة",
        "name_en": "Simple clinic consultation",
        "benefits": {"PRIMARY_CARE"},
        "max_amount": 500,
        "icd_prefixes": ["R50", "J00", "J01", "J02", "J03", "J06", "J11", "K59", "R51"],
        "note_ar": "كشفية عيادة عامة بمبلغ ضمن النطاق الاعتيادي.",
    },
    "BASIC_PHARMACY": {
        "name_ar": "صرف دواء بسيط",
        "name_en": "Basic pharmacy dispense",
        "benefits": {"PRIMARY_CARE"},
        "max_amount": 300,
        "keywords": ["panadol", "paracetamol", "بندول", "باراسيتامول", "مسكن", "خافض حرارة"],
        "note_ar": "صرف دواء بدون وصفة مخصوصة وبمبلغ بسيط.",
    },
    "DENTAL_PREVENTIVE": {
        "name_ar": "فحص وتنظيف أسنان وقائي",
        "name_en": "Preventive dental check-up",
        "benefits": {"DENTAL_BASIC"},
        "max_amount": 600,
        "procedure": ["D0", "D11"],
        "note_ar": "فحص أو تنظيف أسنان وقائي ضمن الحد السنوي.",
    },
    "ROUTINE_LAB": {
        "name_ar": "تحاليل مخبرية روتينية",
        "name_en": "Routine laboratory tests",
        "benefits": {"PRIMARY_CARE"},
        "max_amount": 800,
        "icd_prefixes": ["Z00", "Z01", "Z13"],
        "note_ar": "فحوصات دورية ضمن الرعاية الأولية.",
    },
    "CHRONIC_REFILL": {
        "name_ar": "صرف دوري لعلاج مزمن",
        "name_en": "Chronic medication refill",
        "benefits": {"PRIMARY_CARE"},
        "max_amount": 1_200,
        "requires_chronic_history": True,
        "note_ar": "صرف متكرر لعلاج حالة مزمنة مثبتة في السجل الطبي.",
    },
}

# الحد الأقصى المطلق للأتمتة مهما كانت القاعدة
AUTOMATION_HARD_CEILING = 1_500

# أقصى درجة احتيال مسموحة للأتمتة
AUTOMATION_MAX_FRAUD_SCORE = 10


def _matches_prefix(code, prefixes):
    if not code or not prefixes:
        return False
    upper = str(code).upper().replace(" ", "")
    return any(upper.startswith(p.upper()) for p in prefixes)


def match_automation_rule(benefit_code, amount, diagnosis_code=None,
                          procedure_code=None, description=None, has_chronic=False):
    """يحدد قاعدة الأتمتة المنطبقة، أو None."""
    text = str(description or "").lower()

    for code, rule in AUTOMATION_RULES.items():
        if benefit_code not in rule["benefits"]:
            continue
        if amount > rule["max_amount"]:
            continue
        if rule.get("requires_chronic_history") and not has_chronic:
            continue

        conditions = []
        if rule.get("icd_prefixes"):
            conditions.append(_matches_prefix(diagnosis_code, rule["icd_prefixes"]))
        if rule.get("procedure"):
            conditions.append(_matches_prefix(procedure_code, rule["procedure"]))
        if rule.get("keywords"):
            conditions.append(any(keyword in text for keyword in rule["keywords"]))

        # قاعدة بلا شروط إضافية (مثل المزمن) تمر بمجرد البند والمبلغ
        if not conditions or any(conditions):
            return code, rule

    return None, None


def check_recurring_treatment(user_id, benefit_code, diagnosis_code, amount, service_date=None):
    """يتحقق هل هذه المطالبة علاج دوري معتمد حان موعده."""
    service_date = service_date or date.today()
    if isinstance(service_date, str):
        try:
            service_date = datetime.strptime(service_date[:10], "%Y-%m-%d").date()
        except ValueError:
            service_date = date.today()

    conn = get_connection()
    try:
        rules = conn.execute(
            "SELECT * FROM RecurringTreatments WHERE user_ID = ? AND IsActive = 1",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    for rule in rules:
        if rule["BenefitCode"] != benefit_code:
            continue
        if rule["ConditionCode"] and not _matches_prefix(diagnosis_code, [rule["ConditionCode"]]):
            continue
        if amount > float(rule["MaxAmount"]):
            return {
                "matched": True, "due": False,
                "reason_ar": f"المبلغ {amount:,.2f} يتجاوز سقف العلاج الدوري "
                             f"({float(rule['MaxAmount']):,.2f} ريال).",
                "rule": rule["Description"],
            }

        if rule["LastApproved"]:
            try:
                last = datetime.strptime(str(rule["LastApproved"])[:10], "%Y-%m-%d").date()
            except ValueError:
                last = None
            if last:
                elapsed = (service_date - last).days
                if elapsed < rule["IntervalDays"]:
                    return {
                        "matched": True, "due": False,
                        "reason_ar": f"العلاج الدوري \"{rule['Description']}\" كل "
                                     f"{rule['IntervalDays']} يومًا، ومضى {elapsed} يومًا فقط "
                                     f"منذ آخر صرف.",
                        "rule": rule["Description"],
                    }

        return {
            "matched": True, "due": True,
            "reason_ar": f"علاج دوري معتمد: \"{rule['Description']}\" — حان موعده.",
            "rule": rule["Description"],
            "rule_id": rule["RuleID"],
        }

    return {"matched": False, "due": False, "reason_ar": None, "rule": None}


def mark_recurring_approved(rule_id, service_date=None):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE RecurringTreatments SET LastApproved = ? WHERE RuleID = ?",
            (str(service_date or date.today())[:10], rule_id),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# محرّك القرار الموحّد
# ---------------------------------------------------------------------------

def decide(user_id, amount, diagnosis_code=None, procedure_code=None,
           description=None, claim_type=None, service_date=None,
           member_age=None, member_gender=None, fraud_result=None,
           has_pre_approval=False, claim_id=None):
    """يجمع: البنود + الفئة + التاريخ المرضي + الاحتيال + الأتمتة في قرار واحد.

    يرجع قرارًا نهائيًا مع تبرير كامل يُعرض للموظف.
    """
    policy = get_member_policy(user_id)
    benefit_code, coverage = classify_benefit(
        diagnosis_code, procedure_code, description, claim_type
    )

    used = benefit_usage(user_id, benefit_code, exclude_claim_id=claim_id)
    total_used = annual_usage(user_id, exclude_claim_id=claim_id)

    assessment = evaluate_claim(
        amount=amount,
        diagnosis_code=diagnosis_code,
        procedure_code=procedure_code,
        description=description,
        claim_type=claim_type,
        tier=policy["tier"],
        member_age=member_age,
        member_gender=member_gender,
        used_this_year=used,
        annual_used=total_used,
        has_pre_approval=has_pre_approval,
    )

    clinical = clinical_context_for_claim(
        user_id, diagnosis_code, procedure_code, description, claim_type
    )

    fraud = fraud_result or {"score": 0, "risk_level": "clean", "signals": [],
                             "recommendation": "proceed", "blacklisted": False}

    recurring = check_recurring_treatment(
        user_id, assessment["benefit_code"], diagnosis_code, amount, service_date
    )

    # ---- القرار النهائي ----
    final = assessment["decision"]
    auto = False
    automation_rule = None
    rationale = []

    if fraud["risk_level"] in ("critical", "high"):
        final = "reject" if fraud["risk_level"] == "critical" else "investigate"
        rationale.append({
            "source": "fraud",
            "text_ar": f"درجة الاحتيال {fraud['score']}/100 ({fraud['risk_level']}). "
                       f"عدد الإشارات: {len(fraud['signals'])}.",
            "text_en": f"Fraud score {fraud['score']}/100 ({fraud['risk_level']}) "
                       f"across {len(fraud['signals'])} signals.",
        })
    else:
        rule_code, rule = match_automation_rule(
            assessment["benefit_code"], amount, diagnosis_code, procedure_code,
            description, clinical["has_chronic_match"],
        )

        eligible_for_auto = (
            assessment["decision"] == "approve"
            and amount <= AUTOMATION_HARD_CEILING
            and fraud["score"] <= AUTOMATION_MAX_FRAUD_SCORE
            and (rule is not None or recurring["due"])
        )

        if eligible_for_auto:
            auto = True
            final = "auto_approved"
            automation_rule = rule_code or "RECURRING_TREATMENT"
            reason = recurring["reason_ar"] if recurring["due"] else rule["note_ar"]
            rationale.append({
                "source": "automation",
                "text_ar": f"معالجة آلية — {reason}",
                "text_en": f"Auto-processed — {rule['name_en'] if rule else recurring['rule']}.",
            })
        elif recurring["matched"] and not recurring["due"]:
            rationale.append({
                "source": "automation",
                "text_ar": recurring["reason_ar"],
                "text_en": "Recurring-treatment interval has not elapsed yet.",
            })

    for reason in assessment["reasons"]:
        rationale.append({"source": "policy", "text_ar": reason["text_ar"],
                          "text_en": reason["text_en"]})

    for note in clinical["notes"]:
        rationale.append({"source": note["type"], "text_ar": note["text_ar"],
                          "text_en": note["text_en"]})

    if fraud["signals"] and fraud["risk_level"] not in ("critical", "high"):
        rationale.append({
            "source": "fraud",
            "text_ar": f"درجة الاحتيال {fraud['score']}/100 ({fraud['risk_level']}) — "
                       "ضمن النطاق المقبول.",
            "text_en": f"Fraud score {fraud['score']}/100 ({fraud['risk_level']}) — "
                       "within acceptable range.",
        })

    return {
        "decision": final,
        "auto_processed": auto,
        "automation_rule": automation_rule,
        "benefit": {
            "code": assessment["benefit_code"],
            "name_ar": assessment["benefit_name"],
            "name_en": assessment.get("benefit_name_en"),
            "source_page": assessment.get("source_page"),
        },
        "policy": {
            "tier": policy["tier"],
            "tier_label_ar": policy["tier_label_ar"],
            "insurance_company": policy["insurance_company"],
            "benefit_limit": assessment.get("limit"),
            "benefit_used": round(used, 2),
            "benefit_remaining": assessment.get("remaining"),
            "annual_cap": assessment.get("annual_cap"),
            "annual_used": round(total_used, 2),
            "annual_remaining": assessment.get("annual_remaining"),
        },
        "amounts": {
            "claimed": assessment["claimed"],
            "payable": assessment["payable"],
            "member_share": assessment["member_share"],
            "copay": assessment["copay"],
        },
        "clinical_context": {
            "has_chronic_match": clinical["has_chronic_match"],
            "has_hereditary_match": clinical["has_hereditary_match"],
            "notes": clinical["notes"],
            "conditions": clinical["related_own"],
            "hereditary": clinical["hereditary_context"],
        },
        "fraud": fraud,
        "anomaly": assessment.get("anomaly"),
        "recurring": recurring,
        "rationale": rationale,
    }


# ---------------------------------------------------------------------------
# حفظ القرار واسترجاعه
# ---------------------------------------------------------------------------

import json


def save_claim_decision(claim_id, decision, decided_by="engine"):
    """يخزّن القرار كاملاً ويحدّث أعمدة المطالبة السريعة."""
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO ClaimDecisions
                (ClaimID, BenefitCode, Decision, PayableAmount, MemberShare,
                 FraudScore, AutoProcessed, DecidedBy, Rationale)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                claim_id,
                decision["benefit"]["code"],
                decision["decision"],
                decision["amounts"]["payable"],
                decision["amounts"]["member_share"],
                decision["fraud"]["score"],
                int(decision["auto_processed"]),
                decided_by,
                json.dumps(decision, ensure_ascii=False),
            ),
        )
        conn.execute(
            "UPDATE Claims SET BenefitCode = ?, PayableAmount = ?, FraudScore = ?, "
            "AutoProcessed = ? WHERE ClaimID = ?",
            (
                decision["benefit"]["code"],
                decision["amounts"]["payable"],
                decision["fraud"]["score"],
                int(decision["auto_processed"]),
                claim_id,
            ),
        )

        # الموافقة الآلية تعتمد المطالبة فورًا بدون تدخل الموظف
        if decision["auto_processed"]:
            conn.execute(
                "UPDATE Claims SET ClaimStatus = 'Approved' WHERE ClaimID = ?", (claim_id,)
            )

        conn.commit()
    finally:
        conn.close()


def get_claim_decision(claim_id):
    """يرجع آخر قرار محفوظ للمطالبة، أو None."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT Rationale FROM ClaimDecisions WHERE ClaimID = ? "
            "ORDER BY DecisionID DESC LIMIT 1",
            (claim_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None or not row["Rationale"]:
        return None
    try:
        return json.loads(row["Rationale"])
    except json.JSONDecodeError:
        return None