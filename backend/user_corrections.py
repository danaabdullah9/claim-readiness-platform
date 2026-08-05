"""Separate persistence for member corrections to AI-extracted claim data.

This module deliberately does not write to the claim database. The original claim
record remains the immutable AI snapshot; corrections are stored as a sidecar.
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock


STORE_PATH = Path(__file__).resolve().parent.parent / "database" / "user_corrections.json"
STORE_LOCK = Lock()

CORRECTABLE_FIELDS = {
    "PatientName",
    "MemberId",
    "NationalId",
    "PolicyNumber",
    "InsuranceCompany",
    "InvoiceNumber",
    "InvoiceDate",
    "ServiceDate",
    "HospitalName",
    "ProviderName",
    "ProviderType",
    "City",
    "DiagnosisCode",
    "DiagnosisDescription",
    "Department",
    "DoctorName",
    "ClinicalSummary",
    "TotalAmount",
}


def _read_store():
    if not STORE_PATH.exists():
        return {}
    try:
        with STORE_PATH.open("r", encoding="utf-8") as source:
            data = json.load(source)
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_store(data):
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix="user_corrections_", suffix=".json", dir=STORE_PATH.parent
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as destination:
            json.dump(data, destination, ensure_ascii=False, indent=2)
        os.replace(temporary_name, STORE_PATH)
    finally:
        if os.path.exists(temporary_name):
            os.remove(temporary_name)


def get_user_corrections(claim_id):
    with STORE_LOCK:
        records = _records_for_claim(_read_store().get(str(claim_id)))
        return records[-1] if records else None


def _records_for_claim(stored_claim):
    if isinstance(stored_claim, list):
        return stored_claim
    if isinstance(stored_claim, dict):
        return [stored_claim]
    return []


def has_unresolved_corrections(claim_id):
    """يتفق مع get_user_corrections: يفحص آخر مجموعة تصحيحات مُرسلة بس.

    التصحيحات القديمة اللي انسحبت بإرسال مجموعة جديدة على نفس المطالبة ما
    تعتبر عالقة للأبد لو آخر مجموعة انراجعت.
    """
    with STORE_LOCK:
        records = _records_for_claim(_read_store().get(str(claim_id)))
        if not records:
            return False
        latest_record = records[-1]
        for correction in latest_record.get("corrections", []):
            if correction.get("review_status", "pending") in {
                "pending", "additional_information_required"
            }:
                return True
    return False


def review_user_correction(
    claim_id,
    submitted_at,
    field,
    decision,
    employee_comment=None,
    requested_document_type=None,
    reviewed_by=None,
):
    allowed_decisions = {"accepted", "rejected", "additional_information_required"}
    if decision not in allowed_decisions:
        raise ValueError("Invalid correction review decision")

    comment = str(employee_comment or "").strip()
    document_type = str(requested_document_type or "").strip()
    if decision == "rejected" and not comment:
        raise ValueError("A rejection reason is required")
    if decision == "additional_information_required" and not comment:
        raise ValueError("A supporting document message is required")
    if decision == "additional_information_required" and not document_type:
        raise ValueError("A supporting document type is required")

    with STORE_LOCK:
        store = _read_store()
        stored_claim = store.get(str(claim_id))
        if stored_claim is None:
            raise LookupError("Corrections were not found for this claim")

        matching_record = next(
            (
                record for record in _records_for_claim(stored_claim)
                if record.get("submittedAt") == submitted_at
            ),
            None,
        )
        if matching_record is None:
            raise LookupError("Correction submission was not found")

        correction = next(
            (
                item for item in matching_record.get("corrections", [])
                if item.get("field") == field
            ),
            None,
        )
        if correction is None:
            raise LookupError("Corrected field was not found")
        if correction.get("review_status") in {"accepted", "rejected"}:
            raise ValueError("This correction has already been resolved")

        correction["review_status"] = decision
        correction["reviewed_by"] = reviewed_by or None
        correction["reviewed_at"] = datetime.now(timezone.utc).isoformat()
        correction["employee_comment"] = comment or None
        correction["requested_document_type"] = (
            document_type if decision == "additional_information_required" else None
        )
        correction["final_value"] = (
            correction.get("correctedValue") if decision == "accepted"
            else correction.get("originalValue") if decision == "rejected"
            else None
        )

        _write_store(store)
        return dict(correction)


def save_user_corrections(claim_id, claim, corrections):
    normalized = []
    seen_fields = set()

    for correction in corrections:
        field = correction["field"]
        corrected_value = str(correction["correctedValue"]).strip()
        reason = str(correction.get("reason") or "").strip()

        if field not in CORRECTABLE_FIELDS:
            raise ValueError(f"Field '{field}' cannot be corrected")
        if field in seen_fields:
            raise ValueError(f"Field '{field}' was submitted more than once")
        if not corrected_value:
            raise ValueError(f"A corrected value is required for '{field}'")

        original_value = claim.get(field)
        if str(original_value if original_value is not None else "").strip() == corrected_value:
            raise ValueError(f"The corrected value for '{field}' matches the AI value")

        seen_fields.add(field)
        normalized.append({
            "field": field,
            "originalValue": original_value,
            "correctedValue": corrected_value,
            "reason": reason or None,
        })

    if not normalized:
        raise ValueError("At least one correction is required")

    record = {
        "version": 1,
        "claimId": claim_id,
        "status": "pending",
        "submittedAt": datetime.now(timezone.utc).isoformat(),
        "corrections": normalized,
    }

    with STORE_LOCK:
        store = _read_store()
        existing = store.get(str(claim_id))
        if existing is None:
            store[str(claim_id)] = record
        elif isinstance(existing, list):
            existing.append(record)
        else:
            store[str(claim_id)] = [existing, record]
        _write_store(store)
    return record
