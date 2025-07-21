from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
import logging
from uuid import UUID

from app.services import characters
from app.models.characters import CharacterCreateRequest, CharacterCreateResponse, CharacterUpdateRequest, CharacterUpdateResponse, CharacterStatsUpdateRequest, CharacterStatsUpdateResponse

from app.utils.database import get_db

router = APIRouter(prefix="/characters", tags=["characters"])
ws_router = APIRouter(prefix="/ws/characters", tags=["characters"])
logger = logging.getLogger(__name__)

@router.post("/create", response_model=CharacterCreateResponse, status_code=200)
def character_creation_api(data: CharacterCreateRequest, db: Session = Depends(get_db)):
    """캐릭터 생성"""
    try:
        character = characters.create_character(data, db)
        return {
            "message": "캐릭터 생성 완료",
            "character_id": character.character_id
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    #except Exception as e:
        # 🔥 여기가 핵심: 내부 오류를 확인할 수 있게 함
        #raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")

@ws_router.websocket("/create/{user_id}")
async def character_creation_websocket(
    websocket: WebSocket, 
    user_id: UUID,
    db: Session = Depends(get_db)
):
    character_service = characters.CharacterCreationService(db)
    try:
        await websocket.accept()
        await character_service.prepare_session(str(user_id), websocket)
        await character_service.send_first_question(str(user_id))

        while True:
            try:
                user_message = await websocket.receive_text()
                await character_service.handle_user_message(str(user_id), user_message)
            except WebSocketDisconnect:
                logger.info(f"WebSocket connection closed for user {user_id}")
                break
            except Exception as e:
                logger.error(f"Error handling message for user {user_id}: {str(e)}")
                break

    except Exception as e:
        logger.error(f"Error in WebSocket connection for user {user_id}: {str(e)}")
    finally:
        if str(user_id) in character_service.sessions:
            del character_service.sessions[str(user_id)]
    
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
    
