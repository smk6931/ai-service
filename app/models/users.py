from pydantic import BaseModel, EmailStr

# 요청 모델
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

# 응답 모델
class RegisterResponse(BaseModel):
    message: str

class LoginResponse(BaseModel):
    message: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str

class RefreshResponse(BaseModel):
    message: str
    access_token: str
    token_type: str = "bearer"