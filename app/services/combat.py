from typing import Dict, Any, List
from app.models.combat import (
    CharacterConfig, 
    BattleState, 
    CharacterState, 
    BattleActionResponse,
    MonsterAction,
    BattleStateForAI,
    Character
)
from app.ai.combat import CombatAI

class CombatService:
    def __init__(self):
        self.battle_config_map: Dict[str, Any] = {}
        self.combat_ai = CombatAI()

    async def start_battle(self, characters: List[CharacterConfig], terrain: str, weather: str):
        """전투 시작시 설정을 저장합니다"""
        self.battle_config_map = {
            "characters": {char.id: char for char in characters},
            "terrain": terrain,
            "weather": weather
        }
        return {"status": "success"}

    async def decide_actions(self, state: BattleState) -> BattleActionResponse:
        """AI를 통해 몬스터의 행동을 결정합니다"""
        try:
            # 기본 판단 로직 (AI가 실패할 경우 백업)
            target_id = state.target_monster_id
            monster_state = next((c for c in state.characters if c.id == target_id), None)
            if not monster_state:
                raise ValueError(f"몬스터 ID '{target_id}'를 찾을 수 없습니다.")

            # AI 판단을 위해 BattleState를 BattleStateForAI로 변환
            ai_state = self._convert_to_ai_state(state)
            
            try:
                # AI 판단 시도
                return await self.combat_ai.get_monster_action(ai_state)
            except Exception as e:
                # AI 판단 실패시 기본 로직으로 폴백
                return self._fallback_decision(state)
        
        except Exception as e:
            raise ValueError(f"행동 결정 중 오류 발생: {str(e)}")

    def _convert_to_ai_state(self, state: BattleState) -> BattleStateForAI:
        """BattleState를 AI 판단용 BattleStateForAI로 변환합니다"""
        characters = []
        
        for char_state in state.characters:
            # 캐릭터 ID가 battle_config_map에 있는지 확인
            char_config = self.battle_config_map.get("characters", {}).get(char_state.id)
            
            character = Character(
                id=char_state.id,
                name=char_config.name if char_config else f"Unknown-{char_state.id}",
                type=char_config.type if char_config else "monster",
                position=char_state.position,
                hp=char_state.hp,
                ap=char_state.ap,
                status=char_state.status,
                personality=char_config.personality if char_config else None,
                skills=char_config.skills if char_config else []
            )
            characters.append(character)
        
        return BattleStateForAI(
            characters=characters,
            turn=state.turn,
            target_monster_id=state.target_monster_id,
            terrain=self.battle_config_map.get("terrain", "일반"),
            weather=self.battle_config_map.get("weather", "맑음")
        )

    def _fallback_decision(self, state: BattleState) -> BattleActionResponse:
        """AI 판단 실패시 사용할 기본 판단 로직"""
        target_id = state.target_monster_id
        
        # 적 1명 선택 (monster 제외)
        enemies = [c for c in state.characters if c.id != target_id]
        
        # 스킬은 전투 시작 시 저장된 config에서 가져옴
        monster_config = self.battle_config_map.get("characters", {}).get(target_id)
        skill_list = monster_config.skills if monster_config else ["찌르기"]
        
        actions = []
        if enemies and skill_list:
            actions.append(
                MonsterAction(
                    skill=skill_list[0],
                    target_id=enemies[0].id,
                    reason="기본 판단 로직 사용 (AI 판단 실패)"
                )
            )
        
        return BattleActionResponse(
            monster_id=target_id,
            actions=actions
        ) 