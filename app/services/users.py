from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime

from app.db.users import Users, LoginLog
from app.core.security import get_password_hash, verify_password

def get_active_user_by_email(email: str, db: Session) -> Users | None:
    return db.query(Users).filter(Users.email == email, Users.is_active == True).first()


def register_user(email: str, password: str, db: Session) -> Users:
    existing = get_active_user_by_email(email, db)
    if existing:
        raise ValueError("이미 등록된 이메일입니다.")
    
    user = Users(
        email=email,
        password_hash=get_password_hash(password)
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)


def create_login_log(user_id: UUID, ip: str, user_agent: str, db: Session):
    log = LoginLog(
        user_id=user_id,
        ip_address=ip,
        user_agent=user_agent,
        login_time=datetime.now()
    )
    
    db.add(log)
    db.commit()