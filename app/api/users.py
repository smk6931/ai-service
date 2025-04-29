from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.services import users
from app.services import token

from app.core.security import verify_password, create_access_token, create_refresh_token
from app.core.auth import get_current_user

from app.models.users import RegisterRequest, LoginRequest, RefreshRequest, RegisterResponse, LoginResponse, RefreshResponse

from app.utils.database import get_db

from app.config import settings

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/register", response_model=RegisterResponse, status_code=200)
def register_user(request: RegisterRequest, db: Session = Depends(get_db)):
    try:
        users.register_user(request.email, request.password, db)
        return {
            "message": "회원가입 완료"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=LoginResponse)
def login_user(request: LoginRequest, req: Request, db: Session = Depends(get_db)):
    user = users.get_active_user_by_email(request.email, db)
    if not user:
        raise HTTPException(status_code=404, detail="등록되지 않은 이메일입니다.")
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="비밀번호가 틀렸습니다.")

    users.create_login_log(
        user_id=user.user_id,
        ip=req.client.host,
        user_agent=req.headers.get("user-agent", "unknown"),
        db=db
    )
    
    access_token = create_access_token(
        data={"sub": str(user.user_id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = create_refresh_token(data={"sub": str(user.user_id)})
    refresh_expiry = datetime.now() + timedelta(days=7)

    token.store_refresh_token(db, user.user_id, refresh_token, refresh_expiry)

    return {
        "message": "로그인 성공"
        , "access_token": access_token
        , "refresh_token": refresh_token
        , "user_id": str(user.user_id)
    }


@router.post("/refresh", response_model=RefreshResponse)
def refresh_access_token(request: RefreshRequest, db: Session = Depends(get_db)):
    user_id = token.validate_refresh_token(db, request.refresh_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="유효하지 않은 리프레시 토큰입니다.")

    new_access_token = create_access_token(
        data={"sub": str(user_id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {
        "message": "토큰 갱신 완료"
        , "access_token": new_access_token
    }