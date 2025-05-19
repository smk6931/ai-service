from fastapi import APIRouter, Depends, HTTPException, Body
from app.models.combat import BattleInitRequest, BattleState, BattleActionResponse
from app.services.combat import CombatService
from app.api.examples.combat import (
    BATTLE_START_REQUEST_EXAMPLE,
    BATTLE_START_RESPONSE_EXAMPLE,
    BATTLE_ACTION_REQUEST_EXAMPLE,
    BATTLE_ACTION_RESPONSE_EXAMPLE,
    BATTLE_START_DESCRIPTION,
    BATTLE_ACTION_DESCRIPTION
)

router = APIRouter(prefix="/battle", tags=["battle"])

# 싱글톤 패턴 - 앱 전체에서 하나의 CombatService 인스턴스 사용
combat_service = CombatService()

def get_combat_service():
    return combat_service

@router.post(
    "/start",
    description=BATTLE_START_DESCRIPTION,
    responses={
        200: {
            "description": "전투 시작 성공",
            "content": {
                "application/json": {
                    "example": BATTLE_START_RESPONSE_EXAMPLE
                }
            }
        }
    }
)
async def battle_start(
    request: BattleInitRequest = Body(..., example=BATTLE_START_REQUEST_EXAMPLE), 
    service: CombatService = Depends(get_combat_service)
):
    result = await service.start_battle(
        characters=request.characters,
        terrain=request.terrain,
        weather=request.weather
    )
    return result

@router.post(
    "/action", 
    response_model=BattleActionResponse,
    description=BATTLE_ACTION_DESCRIPTION,
    responses={
        200: {
            "description": "몬스터 행동 결정 성공",
            "content": {
                "application/json": {
                    "example": BATTLE_ACTION_RESPONSE_EXAMPLE
                }
            }
        }
    }
)
async def battle_action(
    state: BattleState = Body(..., example=BATTLE_ACTION_REQUEST_EXAMPLE), 
    service: CombatService = Depends(get_combat_service)
):
    try:
        response = await service.decide_actions(state)
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")
    