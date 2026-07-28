from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import get_connection

app = FastAPI(title="Claim Readiness Platform - Auth")

# السماح للفرونت إند بالاتصال بالباك إند بدون مشاكل CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Structure البيانات المطلوبة من الفرونت إند
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



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)