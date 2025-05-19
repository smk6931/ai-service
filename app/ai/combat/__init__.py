from typing import List, Dict, Optional
from app.models.combat import BattleState, CharacterConfig, CharacterAction, BattleActionResponse, BattleStateForAI, CharacterForAI
from app.utils.combat import calculate_manhattan_distance, calculate_action_costs
from app.ai.combat.graph import run_graph  # LangGraph 실행 함수
from app.ai.combat.states import LangGraphBattleState, Character, ActionPlan


class CombatAI:
    """전투 AI 클래스

    LangGraph를 사용하여 전투 행동을 결정합니다.
    """

    def __init__(self, config_map: Dict[str, CharacterConfig], terrain: str, weather: str):
        self.config_map = config_map
        self.terrain = terrain
        self.weather = weather
        self.battle_log: List[str] = []  # 전투 로그 추가

    async def get_character_action(self, battle_state: BattleState) -> BattleActionResponse:
        """전투 상태를 분석하고 행동 결정"""
        try:
            # LangGraph 실행 시도
            langgraph_state = self._build_langgraph_state(battle_state, self.battle_log)
            result = await run_graph(langgraph_state)
            
            # 결과 변환 및 로그 추가
            response = self._convert_output_to_action(result)
            
            # 행동 로그 추가
            self._add_to_battle_log(response)
            
            return response
            
        except Exception as e:
            # LangGraph 실패 시 폴백 로직 실행
            print(f"AI 판단 실패: {str(e)}")
            return self._fallback_decision(battle_state)

    def _convert_to_ai_state(self, state: BattleState) -> BattleStateForAI:
        """BattleState를 AI 판단용 BattleStateForAI로 변환"""
        characters = []
        
        # 현재 캐릭터 찾기
        current_character = next((c for c in state.characters if c.id == state.current_character_id), None)
        if not current_character:
            raise ValueError(f"현재 캐릭터 ID '{state.current_character_id}'를 찾을 수 없습니다.")
        
        for char_state in state.characters:
            # 캐릭터 설정 가져오기
            char_config = self.config_map.get(char_state.id)
            
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
            terrain=self.terrain,
            weather=self.weather
        )

    def _build_langgraph_state(self, state: BattleState, battle_log: List[str]) -> LangGraphBattleState:
        """LangGraph 실행용 상태 구성"""
        characters: List[Character] = []

        for char_state in state.characters:
            # 캐릭터 설정 가져오기
            char_config = self.config_map.get(char_state.id)
            if char_config is None:
                # 설정 정보가 없으면 기본값 사용
                char_name = f"Unknown-{char_state.id}"
                char_type = "monster"
                char_traits = []
                char_skills = []
            else:
                char_name = char_config.name
                char_type = char_config.type
                char_traits = char_config.traits
                char_skills = char_config.skills

            characters.append(Character(
                id=char_state.id,
                name=char_name,
                type=char_type,
                traits=char_traits,
                skills=char_skills,
                position=char_state.position,
                hp=char_state.hp,
                ap=char_state.ap,
                mov=char_state.mov,
                status_effects=char_state.status_effects
            ))

        return LangGraphBattleState(
            cycle=state.cycle,
            turn=state.turn,
            terrain=self.terrain,
            weather=self.weather,
            current_character_id=state.current_character_id,
            characters=characters,
            battle_log=battle_log
        )

    def _convert_output_to_action(self, state) -> BattleActionResponse:
        """LangGraph 결과를 BattleActionResponse로 변환"""
        # 딕셔너리 형태로 접근
        if isinstance(state, dict):
            if "action_plan" not in state or not state["action_plan"]:
                raise ValueError("LangGraph 결과에서 action_plan이 없거나 비어 있습니다.")
            
            plan = state["action_plan"]
            current_character_id = state["current_character_id"]
        else:
            # 객체 형태로 접근 시도
            if not hasattr(state, "action_plan") or not state.action_plan:
                raise ValueError("LangGraph 결과에서 action_plan이 비어 있습니다.")
            
            plan = state.action_plan
            current_character_id = state.current_character_id
        
        return BattleActionResponse(
            current_character_id=current_character_id,
            action=CharacterAction(
                move_to=plan["move_to"] if isinstance(plan, dict) else plan.move_to,
                skill=plan["skill"] if isinstance(plan, dict) else plan.skill,
                target_character_id=plan["target_character_id"] if isinstance(plan, dict) else plan.target_character_id,
                reason=plan["reason"] if isinstance(plan, dict) else (plan.reason or ""),
                remaining_ap=plan["remaining_ap"] if isinstance(plan, dict) else (plan.remaining_ap or 0),
                remaining_mov=plan["remaining_mov"] if isinstance(plan, dict) else (plan.remaining_mov or 0)
            )
        )
        
    def _fallback_decision(self, state: BattleState) -> BattleActionResponse:
        """AI 판단 실패시 사용할 기본 판단 로직"""
        current_character_id = state.current_character_id
        current_character = next((c for c in state.characters if c.id == current_character_id), None)
        
        if not current_character:
            raise ValueError(f"캐릭터 ID '{current_character_id}'를 찾을 수 없습니다.")
        
        # 필요한 정보 추출
        current_config = self.config_map.get(current_character_id)
        current_type = current_config.type if current_config else "monster"
        
        # 타겟 타입 설정 (몬스터면 플레이어 공격, 플레이어면 몬스터 공격)
        target_type = "player" if current_type == "monster" else "monster"
        
        # 대상 추출
        target_characters = []
        for char in state.characters:
            char_config = self.config_map.get(char.id)
            if char_config and char_config.type == target_type:
                target_characters.append(char)
        
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
        if current_config and current_config.skills:
            skill_name = current_config.skills[0]  # 첫 번째 스킬 사용
        
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
        
    def _add_to_battle_log(self, response: BattleActionResponse) -> None:
        """전투 행동 로그 추가"""
        action = response.action
        log_entry = f"캐릭터 {response.current_character_id}: {action.skill} 사용 -> {action.target_character_id} (이유: {action.reason})"
        self.battle_log.append(log_entry)
        
        # 로그 길이 제한 (최근 20개 항목만 유지)
        if len(self.battle_log) > 20:
            self.battle_log = self.battle_log[-20:]
