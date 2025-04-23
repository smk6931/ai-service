from sqlalchemy import Column, String, Enum, DateTime, ForeignKey, func, Integer, Float, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.db.database import Base
from app.models.characters import JobType, GenderType
    
class Character(Base):
    __tablename__ = "characters"

    character_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)

    character_name = Column(String(10), nullable=False)
    job = Column(Enum(JobType, name="job_enum"), nullable=False)
    gender = Column(Enum(GenderType, name="gender_enum"), nullable=False)
    
    level = Column(Integer, nullable=False, default=1)
    current_exp = Column(Integer, nullable=False, default=0)
    max_exp = Column(Integer, nullable=False, default=100)
    
    position = position = Column(JSON, nullable=False)
    
    created_time = Column(DateTime(timezone=True), server_default=func.now())

    stats = relationship("CharacterStats", back_populates="character", cascade="all, delete-orphan", uselist=False)
    
class CharacterStats(Base):
    __tablename__ = "character_stats"

    character_id = Column(UUID(as_uuid=True), ForeignKey("characters.character_id", ondelete="CASCADE"), primary_key=True)

    hp = Column(Integer, nullable=False, comment="체력")
    attack = Column(Integer, nullable=False, comment="공격력")
    defense = Column(Integer, nullable=False, comment="방어력")
    resistance = Column(Integer, nullable=False, comment="저항력")
    critical_rate = Column(Float, nullable=False, comment="크리티컬 확률 (0~1)")
    critical_damage = Column(Float, nullable=False, comment="크리티컬 데미지 (배수)")
    move_range = Column(Integer, nullable=False, comment="이동 범위")
    speed = Column(Integer, nullable=False, comment="스피드")
    points = Column(Integer, nullable=False, default=0, comment="잔여 스탯 포인트")

    # 관계 설정
    character = relationship("Character", back_populates="stats")