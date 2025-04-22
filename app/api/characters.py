from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.services import characters

from app.models.characters import CharacterCreateRequest, CharacterCreateResponse

from app.db.characters import Character
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
    try:
        characters.create_character(data, db)
        return {
            "message": "캐릭터 생성 완료"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    