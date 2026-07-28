from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import get_connection

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
    report: UploadFile = File(...)
):
    try:
        # استدعاء دالة الـ AI اللي في ملف ai_service.py لمعالجة الفاتورة والتقرير
        result = await analyze_claim(invoice, report)
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)