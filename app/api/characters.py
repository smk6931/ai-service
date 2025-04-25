from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.services import characters

from app.models.characters import CharacterCreateRequest, CharacterCreateResponse, CharacterUpdateRequest, CharacterUpdateResponse, CharacterStatsUpdateRequest, CharacterStatsUpdateResponse

from app.db.database import SessionLocal

router = APIRouter(prefix="/characters", tags=["characters"])

# DB 세션 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/create", response_model=CharacterCreateResponse, status_code=200)
def create_character(data: CharacterCreateRequest, db: Session = Depends(get_db)):
    """캐릭터 생성"""
    try:
        character = characters.create_character(data, db)
        return {
            "message": "캐릭터 생성 완료",
            "character_id": character.character_id
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.put("/update", response_model=CharacterUpdateResponse, status_code=200)
def update_character(data: CharacterUpdateRequest, db: Session = Depends(get_db)):
    """캐릭터 업데이트"""
    try:
        characters.update_character(data, db)
        return {
            "message": "캐릭터 업데이트 완료"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/update_stats", response_model=CharacterStatsUpdateResponse, status_code=200)  
def update_character_stats(data: CharacterStatsUpdateRequest, db: Session = Depends(get_db)):
    """캐릭터 스탯 업데이트"""
    try:
        characters.update_character_stats(data, db)
        return {
            "message": "캐릭터 스탯 업데이트 완료"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
