from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, func, Integer
from sqlalchemy.dialects.postgresql import UUID, INET
import uuid
from app.db.database import Base

class Users(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_time = Column(DateTime, server_default=func.now())
    last_login_time = Column(DateTime, nullable=True)

class LoginLog(Base):
    __tablename__ = "login_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    login_time = Column(DateTime, server_default=func.now())
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    
class RefreshTokens(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(Text, nullable=False)
    created_time = Column(DateTime, server_default=func.now())
    expired_time = Column(DateTime)
    is_valid = Column(Boolean, default=True)