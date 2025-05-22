from typing import Dict, Any, List
from app.models.combat import (
    CharacterConfig, 
    BattleState, 
    BattleActionResponse
)
from app.ai.combat import CombatAI

class CombatService:
    def __init__(self):
        self.battle_config_map: Dict[str, Any] = {}
        self.combat_ai = None

    async def start_battle(self, characters: List[CharacterConfig], terrain: str, weather: str):
        """전투 시작시 설정을 저장합니다"""
        self.battle_config_map = {
            "characters": {char.id: char for char in characters},
            "terrain": terrain,
            "weather": weather
        }
        
        # CombatAI 초기화 - 설정 정보 전달
        self.combat_ai = CombatAI(
            config_map=self.battle_config_map["characters"],
            terrain=terrain,
            weather=weather
        )
        
        return {"status": "success"}

    async def decide_actions(self, state: BattleState) -> BattleActionResponse:
        """AI를 통해 캐릭터의 행동을 결정합니다"""
        try:
            if not self.combat_ai:
                raise ValueError("전투가 시작되지 않았습니다. start_battle을 먼저 호출하세요.")
                
            # AI에 상태 전달하여 행동 결정
            return await self.combat_ai.get_character_action(state)
        
        except Exception as e:
            raise ValueError(f"행동 결정 중 오류 발생: {str(e)}")
        