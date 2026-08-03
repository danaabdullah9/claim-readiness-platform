from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from validation import validate_claim
from database import (
    DuplicateClaimError,
    get_claim_by_id,
    get_connection,
    list_employee_claims,
    save_claim_from_analysis,
    to_employee_claim,
    update_claim_status,
)

# استيراد دالة التحليل من ملف الـ AI الموجود معك في نفس المجلد (backend)
from ai_service import analyze_claim

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

# 🔐 Endpoint تسجيل الدخول
@app.post("/login")
async def login(credentials: LoginRequest):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM USERS
        WHERE email = ? AND password = ?
    """, (credentials.email, credentials.password))

    user = cursor.fetchone()
    conn.close()

    if user:
        return {
            "status": "success",
            "message": "Login successful",
            "user": {
                "id": user["user_ID"],
                "name": user["name"],
                "email": user["email"]
            }
        }

    raise HTTPException(
        status_code=401,
        detail="Invalid email or password"
    )

# 🤖 Endpoint معالجة المطالبات والذكاء الاصطناعي (مرتبط بـ NewClaim.jsx)
@app.post("/api/analyze-claim")
async def analyze_claim_endpoint(
    invoice: UploadFile = File(...),
    report: UploadFile = File(...),
    user_id: Optional[int] = Form(None)
):
    try:
        # استدعاء دالة الـ AI اللي في ملف ai_service.py لمعالجة الفاتورة والتقرير
        result = await analyze_claim(invoice, report)

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

        # حفظ البيانات المستخرجة في الجداول الموجودة وإرجاع رقم المطالبة
        claim_id = save_claim_from_analysis(
            analysis=result,
            invoice_filename=invoice.filename,
            report_filename=report.filename,
            user_id=user_id
        )

        return {
            "status": "success",
            "claim_id": claim_id,
            "data": result
        }
    except DuplicateClaimError as e:
        # شبكة أمان لو وصلت مطالبة مكررة بعد فحص القواعد (سباق بين طلبين)
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
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

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


@app.patch("/api/employee/claims/{claim_id}/status")
async def employee_update_status(claim_id: int, payload: StatusUpdateRequest):
    try:
        updated = update_claim_status(claim_id, payload.status)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not updated:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")

    claim = get_claim_by_id(claim_id)
    return {"status": "success", "data": to_employee_claim(claim)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)