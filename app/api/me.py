from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.database import SessionLocal

from app.models.characters import CharacterInfoRequest, CharacterInfoResponse
from app.models.items import EquipmentGetRequest

from app.services.characters import get_character
from app.services.items import get_character_equipment

router = APIRouter(prefix="/me", tags=["me"])

# DB 세션 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
    
@router.post("/", response_model=CharacterInfoResponse)
def get_me(request: CharacterInfoRequest, db: Session = Depends(get_db)):
    character = get_character(request, db)
    
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

        equipment_info = get_character_equipment(EquipmentGetRequest(character_id=character.character_id), db)
        
    return {
        "message": "정보 조회 완료"
        , "user_id": str(request.user_id)
        , "character_info": character_info
        , "equipment_info": equipment_info
    }