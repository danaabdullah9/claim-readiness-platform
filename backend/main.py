import sys
from typing import Optional

import truststore

# بعض الأجهزة (مضاد فيروسات يفحص اتصالات HTTPS مثلاً) يركّب شهادة جذر خاصة به
# في مخزن شهادات النظام، لكن مكتبات مثل httpx/openai تستخدم حزمة شهادات (certifi)
# منفصلة عن النظام ما تثق فيها، فتفشل الاتصالات الخارجية بخطأ "Connection error"
# غامض. هذا يجبر كل اتصالات SSL في العملية على استخدام شهادات نظام التشغيل.
truststore.inject_into_ssl()

# على ويندوز، الطرفية أحيانًا تستخدم ترميز غير UTF-8 (مثل cp1256) ما يقدر
# يطبع الرموز التعبيرية المستخدمة في رسائل التشخيص (❌📄✅...). بدون هذا،
# أي print() لرمز غير مدعوم يفشل بـ UnicodeEncodeError، وبما إنها ValueError
# فرعيًا، الخطأ الحقيقي ينلبس ويظهر للمستخدم كأنه "بيانات ما تنقرأ من المستند".
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from validation import validate_claim
from verification import build_checklist
from decision_engine import (
    decide,
    get_claim_decision,
    mark_recurring_approved,
    save_claim_decision,
)
from fraud_detection import (
    add_to_blacklist,
    fingerprint_document,
    is_blacklisted,
    list_blacklist,
    remove_from_blacklist,
    save_fingerprint,
    save_signals,
    scan_claim,
)
from member_profile import (
    clinical_context_for_claim,
    get_consent,
    get_family,
    get_medical_history,
    get_member_policy,
    set_consent,
    set_member_tier,
)
from user_corrections import (
    get_user_corrections,
    has_unresolved_corrections,
    review_user_correction,
    save_user_corrections,
)
from database import (
    DuplicateClaimError,
    get_claim_by_id,
    get_connection,
    get_claim_document_file,
    add_claim_notification,
    list_user_claims,
    list_user_notifications,
    list_employee_claims,
    save_claim_from_analysis,
    store_claim_document,
    to_employee_claim,
    update_claim_status,
)

# استيراد دالة التحليل من ملف الـ AI الموجود معك في نفس المجلد (backend)
from ai_service import analyze_documents, read_uploads

app = FastAPI(title="Claim Readiness Platform - Backend")

# السماح للفرونت إند بالاتصال بالباك إند بدون مشاكل CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Structure البيانات المطلوبة لتسجيل الدخول
class LoginRequest(BaseModel):
    email: str
    password: str


class StatusUpdateRequest(BaseModel):
    status: str


class BlacklistRequest(BaseModel):
    user_id: Optional[int] = None
    national_id: Optional[str] = None
    reason: str
    added_by: Optional[str] = "employee"


class TierRequest(BaseModel):
    tier: str


class ConsentRequest(BaseModel):
    share_with_head: Optional[bool] = None
    share_history: Optional[bool] = None


class CorrectionRequest(BaseModel):
    field: str
    correctedValue: str
    reason: Optional[str] = None


class UserCorrectionsRequest(BaseModel):
    corrections: list[CorrectionRequest]


class CorrectionReviewRequest(BaseModel):
    submittedAt: str
    decision: str
    employeeComment: Optional[str] = None
    requestedDocumentType: Optional[str] = None
    reviewedBy: Optional[str] = None

# 🔐 Endpoint تسجيل الدخول
@app.post("/login")
async def login(credentials: LoginRequest):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM Users
        WHERE Email = ? AND Password = ?
    """, (credentials.email, credentials.password))

    user = cursor.fetchone()
    conn.close()

    if user:
        return {
            "status": "success",
            "message": "Login successful",
            "user": {
                "id": user["user_ID"],
                "name": user["Name"],
                "email": user["Email"]
            }
        }

    raise HTTPException(
        status_code=401,
        detail="Invalid email or password"
    )

# 🤖 Endpoint معالجة المطالبات والذكاء الاصطناعي (مرتبط بـ NewClaim.jsx)
@app.post("/api/analyze-claim")
async def analyze_claim_endpoint(
    files: list[UploadFile] = File(...),
    user_id: Optional[int] = Form(None)
):
    """خانة رفع واحدة: أي عدد من الملفات، والقبول يعتمد على اكتمال المعلومات."""
    try:
        if not files:
            raise HTTPException(status_code=400, detail="Attach at least one file.")
        if len(files) > 8:
            raise HTTPException(status_code=400, detail="Attach at most 8 files.")

        entries = await read_uploads(files)
        result = await analyze_documents(entries)

        # قواعد القبول: أي مطالبة ترسب هنا ما تُحفظ ولا يوصل صاحبها لصفحة الملخص
        verdict = validate_claim(result, user_id=user_id)
        if not verdict["eligible"]:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "This claim cannot be submitted.",
                    "rejections": verdict["rejections"],
                },
            )

        # تصنيف الـ AI يحدد نوع كل مستند عند الحفظ
        classified = {
            item.get("file_name"): item.get("type")
            for item in (result.get("documents") or [])
            if item.get("file_name")
        }

        def document_type(name):
            kind = classified.get(name)
            return kind if kind in ("Invoice", "Medical Report", "Prescription") else "Other"

        invoice_name = next(
            (e["filename"] for e in entries if document_type(e["filename"]) == "Invoice"), None
        )
        report_name = next(
            (e["filename"] for e in entries if document_type(e["filename"]) == "Medical Report"),
            invoice_name,  # مستند مدمج يخدم الدورين
        )

        claim_id = save_claim_from_analysis(
            analysis=result,
            invoice_filename=invoice_name or entries[0]["filename"],
            report_filename=report_name or entries[0]["filename"],
            user_id=user_id
        )

        for entry in entries:
            store_claim_document(
                claim_id, document_type(entry["filename"]),
                entry["filename"], entry["content_type"], entry["content"],
            )

        # ---- طبقة الذكاء: بصمة المستندات ← كشف الاحتيال ← قرار البنود ----
        stored = get_claim_by_id(claim_id)
        extracted = result.get("data") or {}

        fingerprints = [
            (entry, fingerprint_document(entry["content"], entry["filename"], entry["content_type"]))
            for entry in entries
        ]
        billing = next(
            (fp for entry, fp in fingerprints if document_type(entry["filename"]) == "Invoice"),
            fingerprints[0][1],
        )
        clinical = next(
            (fp for entry, fp in fingerprints
             if document_type(entry["filename"]) == "Medical Report"),
            None,
        )

        fraud = scan_claim(
            user_id=stored["UserID"],
            invoice_fingerprint=billing,
            report_fingerprint=clinical,
            amount=stored["TotalAmount"],
            provider_name=stored.get("HospitalName"),
            diagnosis_code=stored.get("DiagnosisCode"),
            national_id=stored.get("NationalId"),
        )

        # البصمة تُحفظ بعد الفحص، وإلا طابقت المطالبة نفسها
        for entry, fingerprint in fingerprints:
            save_fingerprint(
                claim_id, stored["UserID"], document_type(entry["filename"]), fingerprint
            )
        save_signals(claim_id, stored["UserID"], fraud["signals"])

        decision = decide(
            user_id=stored["UserID"],
            amount=stored["TotalAmount"],
            diagnosis_code=stored.get("DiagnosisCode"),
            procedure_code=extracted.get("ProcedureCode"),
            description=extracted.get("DiagnosisDescription") or stored.get("DiagnosisDescription"),
            claim_type=stored.get("ClaimType"),
            service_date=stored.get("ServiceDate") or stored.get("InvoiceDate"),
            member_age=extracted.get("Age"),
            member_gender=extracted.get("Gender"),
            fraud_result=fraud,
            claim_id=claim_id,
        )

        save_claim_decision(claim_id, decision)

        if decision["auto_processed"] and decision["recurring"].get("rule_id"):
            mark_recurring_approved(
                decision["recurring"]["rule_id"],
                stored.get("ServiceDate") or stored.get("InvoiceDate"),
            )

        return {
            "status": "success",
            "claim_id": claim_id,
            "data": result,
            "decision": decision,
        }
    except DuplicateClaimError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "This claim cannot be submitted.",
                "rejections": [{
                    "code": "DUPLICATE_CLAIM",
                    "title": "This invoice has already been submitted",
                    "detail": f"{str(e)} It was saved as claim #{e.claim_id}.",
                }],
            },
        )
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "This claim cannot be submitted.",
                "rejections": [{
                    "code": "UNREADABLE_DATA",
                    "title": "A required value could not be read from the documents",
                    "detail": str(e),
                }],
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 📄 Endpoint عرض المطالبة المخزّنة (مرتبط بصفحة Summary.jsx)
@app.get("/api/claims/{claim_id}")
async def get_claim(claim_id: int):
    claim = get_claim_by_id(claim_id)

    if claim is None:
        raise HTTPException(
            status_code=404,
            detail=f"Claim {claim_id} not found"
        )

    return {
        "status": "success",
        "data": claim
    }


@app.get("/api/customers/{user_id}/dashboard")
async def customer_dashboard(user_id: int):
    return {
        "status": "success",
        "data": {
            "claims": list_user_claims(user_id),
            "notifications": list_user_notifications(user_id),
        },
    }


@app.get("/api/claims/{claim_id}/corrections")
async def claim_corrections(claim_id: int):
    if get_claim_by_id(claim_id) is None:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    return {"status": "success", "data": get_user_corrections(claim_id)}


@app.put("/api/claims/{claim_id}/corrections")
async def replace_claim_corrections(claim_id: int, payload: UserCorrectionsRequest):
    claim = get_claim_by_id(claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    try:
        corrections = save_user_corrections(
            claim_id,
            claim,
            [item.dict() for item in payload.corrections],
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    return {"status": "success", "data": corrections}


@app.patch("/api/claims/{claim_id}/corrections/{field}/review")
async def review_claim_correction(
    claim_id: int, field: str, payload: CorrectionReviewRequest
):
    if get_claim_by_id(claim_id) is None:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    try:
        correction = review_user_correction(
            claim_id=claim_id,
            submitted_at=payload.submittedAt,
            field=field,
            decision=payload.decision,
            employee_comment=payload.employeeComment,
            requested_document_type=payload.requestedDocumentType,
            reviewed_by=payload.reviewedBy,
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    return {"status": "success", "data": correction}

# 👩‍💼 Endpoints واجهة الموظف (نفس بيانات المطالبات بشكل مختلف)
@app.post("/api/employee/login")
async def employee_login(credentials: LoginRequest):
    conn = get_connection()
    employee = conn.execute(
        "SELECT * FROM Employees WHERE Email = ? AND Password = ? AND IsActive = 1",
        (credentials.email, credentials.password),
    ).fetchone()
    conn.close()

    if employee:
        return {
            "status": "success",
            "employee": {
                "id": f"EMP{employee['EmployeeID']:04d}",
                "name": employee["FullName"],
                "email": employee["Email"],
                "role": "Claims Specialist",
            },
        }

    raise HTTPException(status_code=401, detail="Invalid employee email or password")


@app.get("/api/employee/claims")
async def employee_claims():
    return {"status": "success", "data": list_employee_claims()}


@app.get("/api/employee/claims/{claim_id}")
async def employee_claim(claim_id: int):
    claim = get_claim_by_id(claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    return {"status": "success", "data": to_employee_claim(claim)}


@app.get("/api/employee/claims/{claim_id}/documents/{document_id}")
async def employee_claim_document(claim_id: int, document_id: int):
    document = get_claim_document_file(claim_id, document_id)
    if document is None:
        raise HTTPException(
            status_code=404,
            detail="The original file is unavailable for this older claim.",
        )
    return FileResponse(
        path=document["path"],
        media_type=document["content_type"],
        filename=document["name"],
        content_disposition_type="inline",
    )


@app.patch("/api/employee/claims/{claim_id}/status")
async def employee_update_status(claim_id: int, payload: StatusUpdateRequest):
    if payload.status == "Approved" and has_unresolved_corrections(claim_id):
        raise HTTPException(
            status_code=409,
            detail="Review all user corrections before approving this claim.",
        )
    notification_copy = {
        "Approved": ("Claim approved", "Your reimbursement claim has been approved."),
        "Rejected": ("Claim decision issued", "Your reimbursement claim was not approved. Open the claim to review the decision."),
        "Pending": ("Claim under review", "Your reimbursement claim is still under review."),
        "Action Required": ("Additional documents required", "Your claims reviewer requested additional supporting documents."),
    }
    if payload.status not in notification_copy:
        raise HTTPException(status_code=422, detail="Unsupported customer-facing claim status.")
    try:
        updated = True if payload.status == "Action Required" else update_claim_status(claim_id, payload.status)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not updated:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")

    title, message = notification_copy[payload.status]
    add_claim_notification(
        claim_id,
        "Document requested" if payload.status == "Action Required" else f"Claim {payload.status.lower()}",
        title,
        message,
        payload.status if payload.status == "Action Required" else None,
    )
    claim = get_claim_by_id(claim_id)
    return {"status": "success", "data": to_employee_claim(claim)}



# 🧠 نقاط نهاية طبقة الذكاء (البنود + الاحتيال + العائلة + التاريخ المرضي)
@app.get("/api/employee/claims/{claim_id}/intelligence")
async def employee_claim_intelligence(claim_id: int):
    """كل ما يحتاجه الموظف لاتخاذ القرار في نداء واحد."""
    claim = get_claim_by_id(claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")

    stored = get_claim_decision(claim_id)
    if stored is not None:
        decision = stored
    else:
        # مطالبة قديمة قبل تفعيل المحرّك: نحسبها الآن بدون حفظ
        fraud = scan_claim(
            user_id=claim["UserID"],
            amount=claim["TotalAmount"],
            provider_name=claim.get("HospitalName"),
            diagnosis_code=claim.get("DiagnosisCode"),
            national_id=claim.get("NationalId"),
        )
        decision = decide(
            user_id=claim["UserID"],
            amount=claim["TotalAmount"],
            diagnosis_code=claim.get("DiagnosisCode"),
            description=claim.get("DiagnosisDescription"),
            claim_type=claim.get("ClaimType"),
            service_date=claim.get("InvoiceDate"),
            fraud_result=fraud,
            claim_id=claim_id,
        )

    return {
        "status": "success",
        "data": {
            **decision,
            "checklist": build_checklist(claim, decision),
            "member": {
                "user_id": claim["UserID"],
                "name": claim.get("PatientName"),
                "national_id": claim.get("NationalId"),
                "blacklisted": is_blacklisted(user_id=claim["UserID"]) is not None,
                "policy": get_member_policy(claim["UserID"]),
                "family": get_family(claim["UserID"]),
                "history": get_medical_history(claim["UserID"]),
            },
        },
    }


@app.get("/api/employee/blacklist")
async def employee_blacklist():
    return {"status": "success", "data": list_blacklist()}


@app.post("/api/employee/blacklist")
async def employee_add_blacklist(payload: BlacklistRequest):
    try:
        entry_id = add_to_blacklist(
            user_id=payload.user_id,
            national_id=payload.national_id,
            reason=payload.reason,
            added_by=payload.added_by,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    return {"status": "success", "entry_id": entry_id, "data": list_blacklist()}


@app.delete("/api/employee/blacklist/{entry_id}")
async def employee_remove_blacklist(entry_id: int):
    remove_from_blacklist(entry_id)
    return {"status": "success", "data": list_blacklist()}


@app.patch("/api/employee/members/{user_id}/tier")
async def employee_set_tier(user_id: int, payload: TierRequest):
    try:
        set_member_tier(user_id, payload.tier)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    return {"status": "success", "data": get_member_policy(user_id)}


# 👨‍👩‍👧 العائلة وموافقات مشاركة البيانات (واجهة العضو)
@app.get("/api/members/{user_id}/family")
async def member_family(user_id: int):
    return {
        "status": "success",
        "data": {
            "policy": get_member_policy(user_id),
            "family": get_family(user_id),
            "consent": get_consent(user_id),
        },
    }


@app.patch("/api/members/{user_id}/consent")
async def member_set_consent(user_id: int, payload: ConsentRequest):
    try:
        consent = set_consent(
            user_id,
            share_with_head=payload.share_with_head,
            share_history=payload.share_history,
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error))
    return {"status": "success", "data": consent}


@app.get("/api/members/{user_id}/history")
async def member_history(user_id: int):
    return {
        "status": "success",
        "data": {
            "conditions": get_medical_history(user_id),
            "policy": get_member_policy(user_id),
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)