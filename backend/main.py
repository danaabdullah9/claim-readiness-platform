from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
    # بيانات التجربة المعتمدة
    if credentials.email == "user@bupa.com" and credentials.password == "123456":
        return {
            "status": "success",
            "message": "Login successful",
            "user": {
                "email": credentials.email,
                "role": "admin"
            }
        }
    else:
        raise HTTPException(
            status_code=401, 
            detail="Invalid email or password"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)