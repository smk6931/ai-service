from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage
from app.ai.combat.states import CombatState
from app.ai.combat.utils import get_current_character, calculate_manhattan_distance, calculate_movable_positions
from app.models.combat import CharacterAction
from app.utils.loader import skills


def generate_action(state: CombatState) -> Dict[str, Any]:
    """행동 생성 노드
    
    전략 및 타겟 정보를 바탕으로 구체적인 행동을 생성합니다.
    
    Args:
        state: 현재 전투 상태
        
    Returns:
        생성된 행동 계획이 포함된 상태 업데이트
    """
    battle_state = state["battle_state"]
    situation_analysis = state["situation_analysis"]
    target_selection = state["target_selection"]
    
    # 현재 캐릭터 정보 확인
    current = get_current_character(battle_state)
    if not current:
        return {
            "planned_actions": [],
            "messages": [SystemMessage(content="[시스템] 행동 생성 중 오류: 현재 캐릭터 정보를 찾을 수 없습니다.")]
        }
    
    # 타겟 정보 확인
    target_id = target_selection.get("target_id")
    approach = target_selection.get("approach", "direct")
    
    if not target_id:
        return {
            "planned_actions": [],
            "messages": [SystemMessage(content="[시스템] 행동 생성 중 오류: 선택된 타겟이 없습니다.")]
        }
    
    # 이동 가능한 위치 계산
    movable_positions = calculate_movable_positions(battle_state)
    
    # AP 및 MOV 리소스
    current_ap = current.ap
    current_mov = current.mov
    current_position = current.position
    
    # 행동 리스트 생성
    planned_actions = []
    remaining_ap = current_ap
    
    # 사용 가능한 스킬 목록
    available_skills = []
    for skill_name in current.skills:
        skill_data = skills.get(skill_name, {})
        skill_ap = skill_data.get('ap', 1)
        skill_range = skill_data.get('range', 1)
        
        if skill_ap <= remaining_ap:
            available_skills.append((skill_name, skill_ap, skill_range))
    
    # 사용 가능한 스킬이 없는 경우
    if not available_skills:
        return {
            "planned_actions": [],
            "messages": [SystemMessage(content="[시스템] 행동 생성 중 오류: 사용 가능한 스킬이 없습니다.")]
        }
    
    # 타겟 위치 및 정보 확인
    target_character = None
    target_position = None
    for character in battle_state.characters:
        if character.id == target_id:
            target_character = character
            target_position = character.position
            break
            
    if not target_position or not target_character:
        return {
            "planned_actions": [],
            "messages": [SystemMessage(content=f"[시스템] 행동 생성 중 오류: 타겟 ID {target_id}의 위치를 찾을 수 없습니다.")]
        }
    
    # 행동 계획 (최대 3개의 행동 시도)
    for attempt in range(min(3, len(available_skills))):
        if not available_skills or remaining_ap <= 0:
            break
            
        # 스킬 선택 (남은 AP에 맞는 스킬 중에서 선택)
        usable_skills = [s for s in available_skills if s[1] <= remaining_ap]
        if not usable_skills:
            break
            
        # 일단 첫 번째 스킬 선택 (추후 더 복잡한 스킬 선택 로직 적용 가능)
        skill_name, skill_ap, skill_range = usable_skills[0]
        available_skills.remove((skill_name, skill_ap, skill_range))
        
        # 현재 위치에서 타겟까지의 거리
        distance_to_target = calculate_manhattan_distance(current_position, target_position)
        
        # 최적 이동 위치 결정
        optimal_position = current_position
        move_required = False
        
        # 타겟이 사거리 밖에 있으면 이동해야 함
        if distance_to_target > skill_range:
            move_required = True
            # 최소한의 이동으로 사거리 내로 들어갈 수 있는 위치 찾기
            best_distance = float('inf')
            for pos in movable_positions:
                move_distance = calculate_manhattan_distance(current_position, pos)
                if move_distance <= current_mov:  # 이동 가능한 거리 내
                    distance_after_move = calculate_manhattan_distance(pos, target_position)
                    if distance_after_move <= skill_range:  # 이동 후 사거리 내
                        total_distance = move_distance + distance_after_move  # 총 이동 거리 + 타겟까지 거리
                        if total_distance < best_distance:
                            best_distance = total_distance
                            optimal_position = pos
            
            # 이동할 위치를 찾지 못했으면 다음 행동으로
            if optimal_position == current_position and distance_to_target > skill_range:
                continue
        
        # 행동 생성 이유 간단하게 작성
        reason = generate_simple_reason(skill_name, target_character, move_required)
        
        # 행동 객체 생성
        action = CharacterAction(
            move_to=optimal_position,
            skill=skill_name,
            target_character_id=target_id,
            reason=reason
        )
        
        # 행동 리스트에 추가
        planned_actions.append(action)
        
        # 리소스 차감 (실제 계산은 다음 단계에서 수행)
        remaining_ap -= skill_ap
        current_position = optimal_position
    
    # 결과 생성
    summary = generate_action_summary(planned_actions)
    
    return {
        "planned_actions": planned_actions,
        "messages": [SystemMessage(content=summary)]
    }


def generate_simple_reason(skill_name: str, target_character: Any, move_required: bool) -> str:
    """간단한 행동 이유를 생성합니다.
    
    Args:
        skill_name: 사용할 스킬 이름
        target_character: 타겟 캐릭터
        move_required: 이동이 필요한지 여부
        
    Returns:
        행동 이유 설명
    """
    if move_required:
        return f"{target_character.name}에게 접근하여 {skill_name} 스킬을 사용하기 위함입니다"
    else:
        return f"{target_character.name}에게 {skill_name} 스킬을 사용하기 위함입니다"


def generate_action_summary(planned_actions: List[CharacterAction]) -> str:
    """행동 계획 요약 메시지를 생성합니다.
    
    Args:
        planned_actions: 계획된 행동 목록
        
    Returns:
        행동 계획 요약
    """
    if not planned_actions:
        return "[시스템] 행동 생성 결과: 실행 가능한 행동이 없습니다."
    
    actions_text = []
    for i, action in enumerate(planned_actions):
        actions_text.append(f"- {i+1}. {action.skill} → {action.target_character_id} (위치: {action.move_to})")
    
    return f"[시스템] 행동 생성 완료: {len(planned_actions)}개의 행동 계획\n" + "\n".join(actions_text) 