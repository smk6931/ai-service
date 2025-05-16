from typing import Dict, Any, List
from app.models.combat import (
    CharacterConfig, 
    BattleState, 
    CharacterState, 
    BattleActionResponse,
    CharacterAction,
    BattleStateForAI,
    CharacterForAI
)
from app.ai.combat import CombatAI
from app.utils.combat import calculate_manhattan_distance, calculate_action_costs

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
        """AI를 통해 캐릭터의 행동을 결정합니다"""
        try:
            # 기본 판단 로직 (AI가 실패할 경우 백업)
            current_character_id = state.current_character_id
            current_character = next((c for c in state.characters if c.id == current_character_id), None)
            if not current_character:
                raise ValueError(f"캐릭터 ID '{current_character_id}'를 찾을 수 없습니다.")

            # AI 판단을 위해 BattleState를 BattleStateForAI로 변환
            ai_state = self._convert_to_ai_state(state)
            
            try:
                # AI 판단 시도 (LangGraph 또는 기존 체인 사용)
                return await self.combat_ai.get_character_action(ai_state)
            except Exception as e:
                # AI 판단 실패시 기본 로직으로 폴백
                print(f"AI 판단 실패: {str(e)}")
                return self._fallback_decision(state)
        
        except Exception as e:
            raise ValueError(f"행동 결정 중 오류 발생: {str(e)}")

    def _convert_to_ai_state(self, state: BattleState) -> BattleStateForAI:
        """BattleState를 AI 판단용 BattleStateForAI로 변환합니다"""
        characters = []
        
        # 현재 캐릭터 찾기
        current_character = next((c for c in state.characters if c.id == state.current_character_id), None)
        if not current_character:
            raise ValueError(f"현재 캐릭터 ID '{state.current_character_id}'를 찾을 수 없습니다.")
        
        
        for char_state in state.characters:
            # 캐릭터 ID가 battle_config_map에 있는지 확인
            char_config = self.battle_config_map.get("characters", {}).get(char_state.id)
            
            # 맨하탄 거리 계산 - 현재 캐릭터와의 거리
            distance = calculate_manhattan_distance(current_character.position, char_state.position)
            
            character = CharacterForAI(
                id=char_state.id,
                name=char_config.name if char_config else f"Unknown-{char_state.id}",
                type=char_config.type if char_config else "monster",
                position=char_state.position,
                hp=char_state.hp,
                ap=char_state.ap,
                mov=char_state.mov,
                status_effects=char_state.status_effects,
                traits=char_config.traits if char_config else [],
                skills=char_config.skills if char_config else [],
                distance=distance
            )
            characters.append(character)
        
        return BattleStateForAI(
            characters=characters,
            cycle=state.cycle,
            turn=state.turn,
            current_character_id=state.current_character_id,
            terrain=self.battle_config_map.get("terrain", "일반"),
            weather=self.battle_config_map.get("weather", "맑음")
        )

    def _fallback_decision(self, state: BattleState) -> BattleActionResponse:
        """AI 판단 실패시 사용할 기본 판단 로직"""
        current_character_id = state.current_character_id
        current_character = next((c for c in state.characters if c.id == current_character_id), None)
        
        if not current_character:
            raise ValueError(f"캐릭터 ID '{current_character_id}'를 찾을 수 없습니다.")
        
        # 필요한 정보 추출
        current_type = self.battle_config_map.get("characters", {}).get(current_character_id, {}).get("type", "monster")
        
        # 타겟 타입 설정 (몬스터면 플레이어 공격, 플레이어면 몬스터 공격)
        target_type = "player" if current_type == "monster" else "monster"
        
        # 대상 추출
        target_characters = [c for c in state.characters if self.battle_config_map.get("characters", {}).get(c.id, {}).get("type", "") == target_type]
        
        if not target_characters:
            # 타겟이 없는 경우, 대기 상태 반환
            action = CharacterAction(
                move_to=current_character.position,
                skill="대기",
                target_character_id=current_character_id,
                reason="공격 대상이 없음",
                remaining_ap=current_character.ap,
                remaining_mov=current_character.mov
            )
            
            return BattleActionResponse(
                current_character_id=current_character_id,
                action=action
            )
        
        # 가장 가까운 타겟 찾기
        target = min(
            target_characters, 
            key=lambda c: calculate_manhattan_distance(current_character.position, c.position)
        )
        
        # 기본 행동 생성
        current_position = current_character.position
        current_ap = current_character.ap
        current_mov = current_character.mov
        
        # 스킬 정보
        skill_name = "타격"  # 기본 스킬
        current_skills = self.battle_config_map.get("characters", {}).get(current_character_id, {}).get("skills", [])
        if current_skills:
            skill_name = current_skills[0]  # 첫 번째 스킬 사용
        
        # 이동할 위치 계산 - 가장 가까운 타겟 방향으로 이동
        move_to_position = current_position
        
        # 움직일 수 있는 경우 타겟쪽으로 한 칸 이동
        if current_mov > 0:
            x1, y1 = current_position
            x2, y2 = target.position
            
            # 방향 계산
            dx = 1 if x2 > x1 else (-1 if x2 < x1 else 0)
            dy = 1 if y2 > y1 else (-1 if y2 < y1 else 0)
            
            # 새 위치 계산 (x 또는 y 중 하나만 이동)
            if dx != 0:
                move_to_position = (x1 + dx, y1)
            elif dy != 0:
                move_to_position = (x1, y1 + dy)
        
        # 행동 비용 계산
        costs = calculate_action_costs(
            from_position=current_position,
            to_position=move_to_position,
            skill_name=skill_name,
            current_ap=current_ap,
            current_mov=current_mov
        )
        
        # 행동 생성
        action = CharacterAction(
            move_to=move_to_position,
            skill=skill_name,
            target_character_id=target.id,
            reason="기본 판단 로직",
            remaining_ap=costs['remaining_ap'],
            remaining_mov=costs['remaining_mov']
        )
        
        # 디버깅 로그
        print(f"폴백 결정: 캐릭터 ID={current_character_id}, 행동={skill_name}")
        
        return BattleActionResponse(
            current_character_id=current_character_id,
            action=action
        )
        