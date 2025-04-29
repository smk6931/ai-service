from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session
from app.core.security import decode_access_token
from app.db.database import SessionLocal
from app.db.users import Users
from app.utils.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")

# # DB 세션 주입
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Users:
    user_id = decode_access_token(token)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 인증 토큰입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(Users).filter(Users.id == user_id, Users.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자를 찾을 수 없습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
