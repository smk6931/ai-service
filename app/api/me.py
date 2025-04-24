from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

# from app.core.auth import get_current_user

from app.db.users import Users
from app.db.characters import Character, CharacterStats
from app.db.database import SessionLocal

router = APIRouter(prefix="/me", tags=["me"])

# DB 세션 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
    
@router.get("/")
def get_me(
    user_id: UUID = Query(..., description="유저 ID"),
    db: Session = Depends(get_db)
):
    character = (
        db.query(Character)
        .filter_by(user_id=user_id)
        .order_by(Character.created_time.desc())
        .first()
    )
    
    if not character:
        raise HTTPException(status_code=404, detail="캐릭터가 존재하지 않습니다.")
    
    if character:
        stats = character.stats
        
        character_info = {
            "character_id": character.character_id,
            "character_name": character.character_name,
            "job": character.job,
            "gender": character.gender,
            "traits": character.traits,
            "level": character.level,
            "current_exp": character.current_exp,
            "max_exp": character.max_exp,
            "position": character.position,
            "stats": {
                "hp": stats.hp,
                "attack": stats.attack,
                "defense": stats.defense,
                "resistance": stats.resistance,
                "critical_rate": stats.critical_rate,
                "critical_damage": stats.critical_damage,
                "move_range": stats.move_range,
                "speed": stats.speed,
                "points": stats.points
            }
        }

    return {
        "message": "정보 조회 완료"
        , "user_id": str(user_id)
        , "character_info": character_info
    }