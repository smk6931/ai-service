from fastapi import APIRouter, Depends, HTTPException
from app.models.combat import BattleInitRequest, BattleState, BattleActionResponse
from app.services.combat_service import CombatService

router = APIRouter(prefix="/battle", tags=["battle"])

# 싱글톤 패턴 - 앱 전체에서 하나의 CombatService 인스턴스 사용
combat_service = CombatService()

def get_combat_service():
    return combat_service

@router.post("/start")
async def battle_start(
    request: BattleInitRequest, 
    service: CombatService = Depends(get_combat_service)
):
    """전투 시작 API - 캐릭터, 지형, 날씨 정보 설정"""
    result = await service.start_battle(
        characters=request.characters,
        terrain=request.terrain,
        weather=request.weather
    )
    return result

@router.post("/action", response_model=BattleActionResponse)
async def battle_action(
    state: BattleState, 
    service: CombatService = Depends(get_combat_service)
):
    """전투 판단 API - 몬스터의 다음 행동 결정"""
    try:
        response = await service.decide_actions(state)
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")
    