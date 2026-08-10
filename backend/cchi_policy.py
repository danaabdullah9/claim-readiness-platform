"""فحص الامتثال لوثيقة الضمان الصحي الأساسية.

المصدر: وثيقة الضمان الصحي الأساسية — مجلس الضمان الصحي التعاوني (CCHI)،
النسخة المحدَّثة، تطبيق 1 أكتوبر 2022.

كل بند هنا مقتبس من الوثيقة ومعه رقم صفحته، فالموظف يستطيع الرجوع للنص
الأصلي، والنظام لا يخترع قاعدة من عنده.
"""

POLICY_NAME = "CCHI Essential Health Insurance Policy"
POLICY_EDITION = "Updated edition — effective 1 October 2022"

# سقف مشاركة المستفيد بالدفع حسب نوع الرعاية (ص42)
COPAY_CAPS = {
    "PRIMARY_CARE": {
        "label": "Primary care visit (family medicine, GP, general paediatrics, "
                 "general internal medicine, general OB/GYN)",
        "rate_max": 0.05,
        "cap": 25,
        "page": 42,
    },
    "SPECIALIST_REFERRED": {
        "label": "Specialist visit with a referral from primary care or emergency",
        "rate_max": 0.10,
        "cap": 75,
        "page": 42,
    },
    "SPECIALIST_DIRECT": {
        "label": "Specialist visit without a referral",
        "rate_max": 0.50,
        "cap": 500,
        "page": 42,
    },
    "MEDICATION_INNOVATIVE": {
        "label": "Innovative medication with no registered generic alternative",
        "rate_max": 0.20,
        "cap": 30,
        "page": 42,
    },
}

# حدود التنويم اليومية (ص43)
INPATIENT_LIMITS = {"patient_daily": 600, "companion_daily": 150, "page": 43}

# البنود التي تنص الوثيقة على أنها بلا مشاركة في الدفع
NO_COPAY_BENEFITS = {"EMERGENCY"}

# مراجع الأقسام في الوثيقة
SECTIONS = {
    "benefits": ("Section 2 — Reimbursable expenses and benefits", 11),
    "exclusions": ("Section 3 — Controls and exclusions", 13),
    "general": ("Section 4 — General conditions", 17),
    "drugs": ("Section 5 — Insured medication guide", 27),
    "network": ("Section 6 — Provider network", 31),
    "schedule": ("Section 7 — Schedule of health benefits", 39),
}


def _item(code, label, state, detail, clause, page, action=None, evidence=None):
    return {
        "id": f"cchi_{code}",
        "group": "CCHI compliance",
        "label": label,
        "state": state,
        "detail": detail,
        "evidence": evidence,
        "action": action,
        "clause": clause,
        "page": page,
    }


def _care_type(claim, benefit_code):
    """يحدد نوع الرعاية لتطبيق سقف المشاركة الصحيح."""
    if benefit_code in NO_COPAY_BENEFITS:
        return None

    department = str(claim.get("Department") or "").lower()
    claim_type = str(claim.get("ClaimType") or "").lower()

    primary_markers = ("general medicine", "family", "gp", "general practice",
                       "paediatr", "pediatr", "internal medicine", "primary")
    if any(marker in department for marker in primary_markers):
        return "PRIMARY_CARE"

    if "pharmac" in department or "pharmac" in claim_type:
        return "MEDICATION_INNOVATIVE"

    # كل ما عدا ذلك عيادة تخصصية؛ الوثيقة تفرّق بين المحوّل وغير المحوّل،
    # ولا يوجد حقل تحويل في المستندات، فنطبّق السقف الأعلى تحفّظًا.
    return "SPECIALIST_DIRECT"


def check_compliance(claim, decision):
    """يرجع بنود امتثال الوثيقة لهذه المطالبة."""
    items = []
    benefit = decision["benefit"]
    policy = decision["policy"]
    amounts = decision["amounts"]
    benefit_code = benefit["code"]

    # 1) البند ضمن جدول المنافع الإلزامي
    section, page = SECTIONS["schedule"]
    items.append(_item(
        "scope", "Benefit listed in the mandatory schedule", "pass",
        f"“{benefit['name_en']}” appears in the schedule of health benefits "
        f"({section}), page {benefit['source_page']} of the policy document.",
        section, benefit["source_page"], evidence=benefit["name_en"],
    ))

    # 2) الاستثناءات
    section, page = SECTIONS["exclusions"]
    excluded = decision["decision"] == "reject" and any(
        reason.get("code") == "NOT_COVERED" for reason in []
    )
    is_excluded = benefit_code in ("COSMETIC", "FERTILITY")
    items.append(_item(
        "exclusions", "Not an excluded service",
        "fail" if is_excluded else "pass",
        f"“{benefit['name_en']}” is listed among the excluded services in {section}."
        if is_excluded else
        f"The service does not appear in the exclusions listed in {section}.",
        section, page,
        action="Excluded services cannot be reimbursed under the essential policy."
        if is_excluded else None,
    ))

    # 3) سقف المنفعة
    limit = policy.get("benefit_limit")
    if limit:
        after = policy["benefit_used"] + amounts["payable"]
        within = after <= limit
        items.append(_item(
            "ceiling", "Within the regulated benefit ceiling",
            "pass" if within else "fail",
            f"The policy caps “{benefit['name_en']}” at SAR {limit:,.2f} for the policy "
            f"period. SAR {after:,.2f} is used after this claim.",
            "Schedule of health benefits", benefit["source_page"],
            evidence=f"SAR {after:,.2f} / SAR {limit:,.2f}",
            action=None if within else
            "Coverage stops once the benefit maximum is exhausted (Section 4, page 18).",
        ))
    else:
        items.append(_item(
            "ceiling", "Benefit ceiling", "pass",
            f"“{benefit['name_en']}” has no separate ceiling in the schedule; it is "
            f"paid against the overall annual maximum of the policy.",
            "Schedule of health benefits", benefit["source_page"],
        ))

    # 4) سقف المشاركة في الدفع
    care_type = _care_type(claim, benefit_code)
    copay = amounts["copay"]

    if benefit_code in NO_COPAY_BENEFITS:
        items.append(_item(
            "copay", "Co-payment rule for emergency care",
            "pass" if copay == 0 else "fail",
            "Emergency treatment is provided without deducting a co-payment from "
            "the member." if copay == 0 else
            f"A co-payment of SAR {copay:,.2f} was applied to an emergency claim, "
            "which the policy does not allow.",
            "Section 2 — Emergency treatment", 42,
            action=None if copay == 0 else "Remove the co-payment before paying.",
        ))
    elif care_type:
        rule = COPAY_CAPS[care_type]
        rate = (copay / amounts["claimed"]) if amounts["claimed"] else 0
        within_rate = rate <= rule["rate_max"] + 1e-6
        within_cap = copay <= rule["cap"] + 1e-6
        compliant = within_rate and within_cap

        items.append(_item(
            "copay", "Co-payment within the regulated cap",
            "pass" if compliant else "fail",
            f"{rule['label']}: the policy allows up to {rule['rate_max']:.0%} with a "
            f"maximum of SAR {rule['cap']:,.0f} per visit. This claim applies "
            f"SAR {copay:,.2f} ({rate:.0%}).",
            "Co-payment by type of care", rule["page"],
            evidence=f"SAR {copay:,.2f} of max SAR {rule['cap']:,.0f}",
            action=None if compliant else
            f"Reduce the member's share to at most SAR {rule['cap']:,.0f}.",
        ))

    # 5) حدود التنويم اليومية
    if benefit_code == "INPATIENT_ROOM":
        items.append(_item(
            "inpatient", "Daily room and board limit", "warn",
            f"The policy caps room and board at SAR {INPATIENT_LIMITS['patient_daily']:,} "
            f"per day for the patient and SAR {INPATIENT_LIMITS['companion_daily']:,} per "
            f"day for a companion. Confirm the number of nights on the invoice.",
            "Inpatient expenses", INPATIENT_LIMITS["page"],
            action="Divide the invoice total by the number of nights and compare.",
        ))

    # 6) الموافقة المسبقة
    needs_pre_approval = decision["decision"] == "pre_approval_required"
    items.append(_item(
        "preapproval", "Pre-approval requirement",
        "warn" if needs_pre_approval else "pass",
        f"“{benefit['name_en']}” requires the insurer's approval before the service "
        f"is provided." if needs_pre_approval else
        f"“{benefit['name_en']}” does not require pre-approval.",
        SECTIONS["general"][0], SECTIONS["general"][1],
        action="Confirm a pre-approval reference before settling."
        if needs_pre_approval else None,
    ))

    # 7) المنشأة مرخّصة ضمن الشبكة
    provider = claim.get("HospitalName")
    items.append(_item(
        "network", "Provider identified on the invoice",
        "pass" if provider else "fail",
        f"The invoice was issued by “{provider}”, which must belong to the insurer's "
        f"approved network under {SECTIONS['network'][0]}." if provider else
        "No issuing facility could be read from the invoice.",
        SECTIONS["network"][0], SECTIONS["network"][1],
        evidence=provider,
        action=None if provider else "A licensed provider must be identifiable on the invoice.",
    ))

    return items


def policy_reference():
    """بطاقة تعريف الوثيقة تُعرض للموظف."""
    return {
        "name": POLICY_NAME,
        "edition": POLICY_EDITION,
        "sections": [
            {"title": title, "page": page} for title, page in SECTIONS.values()
        ],
    }
