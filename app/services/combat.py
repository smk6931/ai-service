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
                # AI 판단 시도
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
        
        # 타겟 캐릭터의 위치 찾기
        current_character = next((c for c in state.characters if c.id == state.current_character_id), None)
        if not current_character:
            raise ValueError(f"타겟 몬스터 ID '{state.current_character_id}'를 찾을 수 없습니다.")
        
        
        for char_state in state.characters:
            # 캐릭터 ID가 battle_config_map에 있는지 확인
            char_config = self.battle_config_map.get("characters", {}).get(char_state.id)
            
            # 맨하탄 거리 계산 - 타겟 몬스터와의 거리
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
        
        # 현재 캐릭터 상태 가져오기
        current_character = next((c for c in state.characters if c.id == current_character_id), None)
        if not current_character:
            raise ValueError(f"캐릭터 ID '{current_character_id}'를 찾을 수 없습니다.")
        
        # 타겟 캐릭터 선택
        target_characters = [c for c in state.characters if c.id != current_character_id]
        
        # 스킬은 전투 시작 시 저장된 config에서 가져옴
        current_config = self.battle_config_map.get("characters", {}).get(current_character_id)
        skill_list = current_config.skills if current_config and current_config.skills else ["찌르기"]
        
        actions = []
        if target_characters and skill_list:
            # 현재 리소스 상태
            current_ap = current_character.ap
            current_mov = current_character.mov
            current_position = current_character.position
            
            # 가장 가까운 타겟 찾기
            target_characters.sort(key=lambda c: calculate_manhattan_distance(current_position, c.position))
            
            # 최대 2개 행동 시도 (가능한 경우)
            for i in range(min(2, len(skill_list))):
                if i >= len(target_characters):
                    break
                
                target = target_characters[i]
                skill_name = skill_list[i]
                
                # 스킬 AP 소모량 가져오기
                skill_ap_cost = 1  # 기본값
                from app.utils.loader import skills
                if skill_name in skills:
                    skill_ap_cost = skills[skill_name].get('ap', 1)
                
                # 타겟과의 거리 계산
                distance_to_target = calculate_manhattan_distance(current_position, target.position)
                
                # 스킬 사거리 가져오기
                skill_range = 1  # 기본 사거리
                if skill_name in skills:
                    skill_range = skills[skill_name].get('range', 1)
                
                # 이동해야 할 위치 계산 (사거리 내로)
                move_to_position = current_position
                if distance_to_target > skill_range:
                    # 사거리 내로 가는 최소 이동 계산
                    # 단순화를 위해 X축 방향으로 우선 이동
                    dx = target.position[0] - current_position[0]
                    dy = target.position[1] - current_position[1]
                    
                    # 이동 거리 계산 (사거리에 맞게 조정)
                    move_distance = distance_to_target - skill_range
                    
                    # X축 이동
                    x_move = min(abs(dx), move_distance) * (1 if dx > 0 else -1 if dx < 0 else 0)
                    remaining_move = move_distance - abs(x_move)
                    
                    # Y축 이동
                    y_move = min(abs(dy), remaining_move) * (1 if dy > 0 else -1 if dy < 0 else 0)
                    
                    move_to_position = (
                        current_position[0] + x_move,
                        current_position[1] + y_move
                    )
                
                # 이동 및 스킬 사용 비용 계산
                costs = calculate_action_costs(
                    current_position=current_position,
                    target_position=move_to_position,
                    current_ap=current_ap,
                    current_mov=current_mov,
                    skill_ap_cost=skill_ap_cost
                )
                
                # 행동 가능 여부 확인
                if not costs['can_perform']:
                    break
                
                # 행동 추가
                actions.append(
                    CharacterAction(
                        move_to=move_to_position,
                        skill=skill_name,
                        target_character_id=target.id,
                        reason=f"기본 판단 로직: {i+1}번째 행동",
                        remaining_ap=costs['remaining_ap'],
                        remaining_mov=costs['remaining_mov']
                    )
                )
                
                # 다음 행동을 위한 상태 업데이트
                current_ap = costs['remaining_ap']
                current_mov = costs['remaining_mov']
                current_position = move_to_position
        
        return BattleActionResponse(
            current_character_id=current_character_id,
            actions=actions
        ) 