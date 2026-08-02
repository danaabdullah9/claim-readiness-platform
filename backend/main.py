from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import (
    DuplicateClaimError,
    get_claim_by_id,
    get_connection,
    save_claim_from_analysis,
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
        raise HTTPException(
            status_code=409,
            detail={"message": str(e), "claim_id": e.claim_id}
        )
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=str(e)
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)