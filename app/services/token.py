from sqlalchemy.orm import Session
from datetime import datetime
from uuid import UUID
from app.db.users import RefreshTokens

def store_refresh_token(db: Session, user_id: UUID, token: str, expire_time: datetime):
    db_token = RefreshTokens(
        user_id=user_id,
        token=token,
        expired_time=expire_time,
        is_valid=True
    )
    db.add(db_token)
    db.commit()


def validate_refresh_token(db: Session, token: str) -> UUID | None:
    db_token = db.query(RefreshTokens).filter(
        RefreshTokens.token == token,
        RefreshTokens.is_valid == True,
        RefreshTokens.expired_time > datetime.utcnow()
    ).first()

    if not db_token:
        return None

    return db_token.user_id


def invalidate_refresh_token(db: Session, token: str):
    db_token = db.query(RefreshTokens).filter(RefreshTokens.token == token).first()
    if db_token:
        db_token.is_valid = False
        db.commit()
