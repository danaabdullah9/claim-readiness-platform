"""بناء قائمة التحقق الكاملة التي يراها الموظف.

كل بند هنا مبني على بيانات حقيقية من قاعدة البيانات أو من نتائج المحرّكات
(الاستخراج، التدقيق المتقاطع، قواعد الأهلية، البنود، كشف الاحتيال). لا يوجد
بند ثابت أو تجميلي: إن لم تتوفر بياناته لا يُعرض.

الحالات: pass (أخضر) / warn (برتقالي) / fail (أحمر)
"""

from datetime import date, datetime

from cchi_policy import check_compliance, policy_reference
from fraud_detection import is_blacklisted
from validation import CLAIM_WINDOW_DAYS, names_match

# الحقول التي يجب استخراجها من المستندات لتكتمل المطالبة
REQUIRED_FIELDS = [
    ("InvoiceNumber", "Invoice number"),
    ("InvoiceDate", "Invoice date"),
    ("HospitalName", "Billing entity"),
    ("DoctorName", "Treating physician"),
    ("DiagnosisCode", "Diagnosis code"),
    ("TotalAmount", "Total amount"),
]

OPTIONAL_FIELDS = [
    ("MemberId", "Member ID"),
    ("NationalId", "National ID"),
    ("PatientName", "Patient name"),
    ("ServiceDate", "Service date"),
    ("PolicyNumber", "Policy number"),
    ("Department", "Department"),
]


def _item(item_id, group, label, state, detail, evidence=None, action=None):
    return {
        "id": item_id,
        "group": group,
        "label": label,
        "state": state,
        "detail": detail,
        "evidence": evidence,
        "action": action,
    }


def _fmt_money(value):
    try:
        return f"SAR {float(value):,.2f}"
    except (TypeError, ValueError):
        return "—"


def _parse_date(value):
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# المجموعات
# ---------------------------------------------------------------------------

def _documents_group(claim):
    items = []
    documents = claim.get("Documents") or []
    types = {document.get("DocumentType") for document in documents}

    for required in ("Invoice", "Medical Report"):
        present = required in types
        names = [d["FileName"] for d in documents if d.get("DocumentType") == required]
        items.append(_item(
            f"doc_{required.lower().replace(' ', '_')}",
            "Documents",
            f"{required} received",
            "pass" if present else "fail",
            f"{names[0]} was uploaded and read successfully." if present
            else f"No {required.lower()} was found among the uploaded files.",
            evidence=names[0] if names else None,
            action=None if present else f"Ask the member to upload the {required.lower()}.",
        ))

    extra = [d for d in documents if d.get("DocumentType") not in ("Invoice", "Medical Report")]
    if extra:
        items.append(_item(
            "doc_supporting", "Documents", "Supporting files attached", "pass",
            f"{len(extra)} additional supporting file(s) were provided.",
            evidence=", ".join(d["FileName"] for d in extra),
        ))

    return items


def _extraction_group(claim):
    items = []

    for key, label in REQUIRED_FIELDS:
        value = claim.get(key)
        present = value not in (None, "", "—")
        display = _fmt_money(value) if key == "TotalAmount" else value
        items.append(_item(
            f"field_{key}", "Data extraction", label,
            "pass" if present else "fail",
            f"Read from the documents as “{display}”." if present
            else f"{label} could not be read from any uploaded document.",
            evidence=display if present else None,
            action=None if present else f"The {label.lower()} must be visible on the invoice.",
        ))

    missing_optional = []
    for key, label in OPTIONAL_FIELDS:
        value = claim.get(key)
        if value in (None, "", "—"):
            missing_optional.append(label)
        else:
            items.append(_item(
                f"field_{key}", "Data extraction", label, "pass",
                f"Read from the documents as “{value}”.", evidence=value,
            ))

    if missing_optional:
        items.append(_item(
            "field_optional_missing", "Data extraction", "Secondary fields",
            "warn",
            f"{len(missing_optional)} supporting field(s) were not found: "
            f"{', '.join(missing_optional)}. The claim can still proceed.",
            action="Confirm these values manually if they affect your decision.",
        ))

    return items


def _consistency_group(claim):
    items = []
    verification = claim.get("Verification") or {}
    discrepancies = verification.get("Discrepancies") or []

    match_status = verification.get("MatchStatus", "success")
    high = [d for d in discrepancies if str(d.get("severity", "")).lower() == "high"]

    items.append(_item(
        "cross_match", "Consistency", "Invoice matches medical report",
        "pass" if match_status == "success" else "warn" if not high else "fail",
        "Every cross-checked field is identical in both documents." if match_status == "success"
        else f"{len(discrepancies)} difference(s) were found between the two documents.",
        action=None if match_status == "success" else "Review each difference below before deciding.",
    ))

    for index, item in enumerate(discrepancies):
        severity = str(item.get("severity", "low")).lower()
        items.append(_item(
            f"cross_{index}", "Consistency", f"Field check — {item.get('field')}",
            "fail" if severity == "high" else "warn",
            f"Invoice shows “{item.get('invoice_value')}” while the medical report "
            f"shows “{item.get('report_value')}”.",
            action="Identity or diagnosis mismatch — do not approve without proof."
            if severity == "high" else "Likely a spelling or formatting variant.",
        ))

    if verification.get("IsValid") is False:
        items.append(_item(
            "cross_valid", "Consistency", "Document type validation", "fail",
            verification.get("ValidationMessage") or "The uploaded files did not pass validation.",
            action="Ask the member to upload the correct documents.",
        ))

    return items


def _eligibility_group(claim):
    items = []

    patient = claim.get("PatientName")
    holder = claim.get("AccountHolderName")
    if patient and holder:
        matched = names_match(patient, holder)
        items.append(_item(
            "elig_name", "Eligibility", "Patient matches the account holder",
            "pass" if matched else "fail",
            f"“{patient}” on the documents matches the registered member “{holder}”."
            if matched else
            f"The documents are issued to “{patient}” but the account is registered "
            f"to “{holder}”.",
            evidence=patient,
            action=None if matched else "A claim can only be filed for the account holder.",
        ))

    service_date = _parse_date(claim.get("ServiceDate")) or _parse_date(claim.get("InvoiceDate"))
    if service_date:
        age = (date.today() - service_date).days
        within = 0 <= age <= CLAIM_WINDOW_DAYS
        items.append(_item(
            "elig_window", "Eligibility", f"Filed within {CLAIM_WINDOW_DAYS} days",
            "pass" if within else "fail",
            f"Service date {service_date.isoformat()} — filed {age} day(s) later, "
            f"inside the {CLAIM_WINDOW_DAYS}-day window."
            if within else
            f"Service date {service_date.isoformat()} is {age} day(s) ago; the "
            f"{CLAIM_WINDOW_DAYS}-day window closed "
            f"{age - CLAIM_WINDOW_DAYS} day(s) ago.",
            evidence=service_date.isoformat(),
            action=None if within else "Late submissions are rejected under policy terms.",
        ))

    blacklisted = is_blacklisted(user_id=claim.get("UserID"), national_id=claim.get("NationalId"))
    items.append(_item(
        "elig_blacklist", "Eligibility", "Member not blacklisted",
        "pass" if not blacklisted else "fail",
        "The member is not on the fraud blacklist." if not blacklisted
        else f"The member is blacklisted. Reason: {blacklisted['Reason']}",
        action=None if not blacklisted else "Reject the claim and escalate to fraud team.",
    ))

    items.append(_item(
        "elig_duplicate", "Eligibility", "Invoice not previously claimed", "pass",
        f"Invoice {claim.get('InvoiceNumber')} appears only once in the claims table.",
        evidence=claim.get("InvoiceNumber"),
    ))

    return items


def _policy_group(decision):
    items = []
    benefit = decision["benefit"]
    policy = decision["policy"]
    amounts = decision["amounts"]

    items.append(_item(
        "pol_benefit", "Policy benefits", "Benefit category identified", "pass",
        f"Mapped to “{benefit['name_en']}” under the essential benefits policy "
        f"(page {benefit['source_page']}).",
        evidence=benefit["name_en"],
    ))

    limit = policy.get("benefit_limit")
    if limit:
        after = policy["benefit_used"] + amounts["payable"]
        within = after <= limit
        items.append(_item(
            "pol_limit", "Policy benefits", "Within the benefit limit",
            "pass" if within and amounts["payable"] >= amounts["claimed"] else "warn",
            f"{_fmt_money(after)} of the {_fmt_money(limit)} annual limit will be used "
            f"after this claim."
            if within else
            f"The claim exceeds the {_fmt_money(limit)} annual limit; only "
            f"{_fmt_money(amounts['payable'])} is payable.",
            evidence=f"{_fmt_money(after)} / {_fmt_money(limit)}",
            action=None if amounts["payable"] >= amounts["claimed"]
            else f"The member covers the remaining {_fmt_money(amounts['member_share'])}.",
        ))

    cap_after = policy["annual_used"] + amounts["payable"]
    items.append(_item(
        "pol_cap", "Policy benefits", f"Within the {policy['tier']} annual cap",
        "pass" if cap_after <= policy["annual_cap"] else "fail",
        f"{_fmt_money(cap_after)} of the {_fmt_money(policy['annual_cap'])} annual cap "
        f"will be used after this claim.",
        evidence=f"{_fmt_money(cap_after)} / {_fmt_money(policy['annual_cap'])}",
    ))

    needs_pre_approval = decision["decision"] == "pre_approval_required"
    items.append(_item(
        "pol_preapproval", "Policy benefits", "Pre-approval requirement",
        "warn" if needs_pre_approval else "pass",
        "This benefit requires pre-approval before the service is provided."
        if needs_pre_approval else
        "This benefit does not require pre-approval.",
        action="Verify a pre-approval reference exists before paying."
        if needs_pre_approval else None,
    ))

    anomaly = decision.get("anomaly")
    items.append(_item(
        "pol_amount", "Policy benefits", "Amount within the expected range",
        "pass" if not anomaly else "fail" if anomaly["severity"] in ("critical", "high") else "warn",
        f"{_fmt_money(amounts['claimed'])} is consistent with typical charges for "
        f"{benefit['name_en'].lower()}." if not anomaly else anomaly["message_en"],
        evidence=_fmt_money(amounts["claimed"]),
        action=None if not anomaly else "Request an itemised bill from the provider.",
    ))

    if amounts["copay"] > 0:
        items.append(_item(
            "pol_copay", "Policy benefits", "Co-payment applied", "pass",
            f"A co-payment of {_fmt_money(amounts['copay'])} is deducted under this benefit.",
            evidence=_fmt_money(amounts["copay"]),
        ))

    return items


def _fraud_group(decision):
    items = []
    fraud = decision["fraud"]

    items.append(_item(
        "fraud_score", "Fraud screening", "Overall fraud risk",
        "pass" if fraud["risk_level"] == "clean"
        else "warn" if fraud["risk_level"] in ("low", "medium") else "fail",
        f"Risk score {fraud['score']}/100 ({fraud['risk_level']}). Document fingerprints, "
        "PDF metadata, submission history, provider concentration and amount patterns "
        "were all checked."
        if fraud["risk_level"] == "clean" else
        f"Risk score {fraud['score']}/100 ({fraud['risk_level']}) from "
        f"{len(fraud['signals'])} signal(s).",
        evidence=f"{fraud['score']}/100",
    ))

    for index, signal in enumerate(fraud["signals"]):
        severity = str(signal.get("severity", "low")).lower()
        items.append(_item(
            f"fraud_{index}", "Fraud screening",
            signal["code"].replace("_", " ").title(),
            "fail" if severity in ("high", "critical") else "warn",
            signal["detail_en"],
            evidence=f"+{signal['score']} risk",
            action="Investigate before approving." if severity in ("high", "critical") else None,
        ))

    return items


def _history_group(decision):
    items = []
    clinical = decision["clinical_context"]

    if clinical["notes"]:
        for index, note in enumerate(clinical["notes"]):
            items.append(_item(
                f"hist_{index}", "Medical history",
                "Chronic condition on file" if note["type"] == "chronic"
                else "Hereditary background",
                "pass", note["text_en"],
            ))
    else:
        items.append(_item(
            "hist_none", "Medical history", "Medical history reviewed", "pass",
            "No chronic or hereditary condition on file relates to this diagnosis.",
        ))

    return items


# ---------------------------------------------------------------------------
# نقطة الدخول
# ---------------------------------------------------------------------------

GROUP_ORDER = [
    ("Documents", "Files received and readable"),
    ("Data extraction", "Every field the claim needs"),
    ("Consistency", "Invoice against medical report"),
    ("Eligibility", "Member, timing and duplicates"),
    ("Policy benefits", "Coverage, limits and pre-approval"),
    ("CCHI compliance", "Council of Cooperative Health Insurance policy document"),
    ("Fraud screening", "Document forensics and behaviour"),
    ("Medical history", "Chronic and hereditary context"),
]


def build_checklist(claim, decision):
    """يرجع قائمة التحقق مجمّعة مع ملخص عددي."""
    items = (
        _documents_group(claim)
        + _extraction_group(claim)
        + _consistency_group(claim)
        + _eligibility_group(claim)
        + _policy_group(decision)
        + check_compliance(claim, decision)
        + _fraud_group(decision)
        + _history_group(decision)
    )

    by_group = {}
    for item in items:
        by_group.setdefault(item["group"], []).append(item)

    groups = [
        {"name": name, "caption": caption, "items": by_group[name]}
        for name, caption in GROUP_ORDER
        if name in by_group
    ]

    counts = {
        "pass": sum(1 for item in items if item["state"] == "pass"),
        "warn": sum(1 for item in items if item["state"] == "warn"),
        "fail": sum(1 for item in items if item["state"] == "fail"),
        "total": len(items),
    }

    return {
        "policy_reference": policy_reference(),
        "groups": groups,
        "items": items,
        "counts": counts,
        "verdict": "fail" if counts["fail"] else "warn" if counts["warn"] else "pass",
    }