from typing import Dict, Any, List, Tuple
from langchain_core.messages import SystemMessage
from app.ai.combat.states import CombatState
from app.ai.combat.utils import get_current_character
from app.models.combat import CharacterAction
from app.utils.combat import calculate_action_costs
from app.utils.loader import skills
from app.ai.combat.nodes import debug_node


def calculate_resources(state: CombatState) -> Dict[str, Any]:
    """리소스 계산 노드
    
    행동에 필요한 AP와 MOV를 계산하고 리소스 부족 시 행동을 조정합니다.
    
    Args:
        state: 현재 전투 상태
        
    Returns:
        최종 행동 계획이 포함된 상태 업데이트
    """
    battle_state = state["battle_state"]
    planned_actions = state.get("planned_actions", [])
    
    # 현재 캐릭터 정보 확인
    current = get_current_character(battle_state)
    if not current:
        return {
            "final_actions": [],
            "resource_calculation": {"error": "현재 캐릭터를 찾을 수 없습니다"},
            "messages": [SystemMessage(content="[시스템] 리소스 계산 중 오류: 현재 캐릭터 정보를 찾을 수 없습니다.")]
        }
    
    # 계획된 행동이 없는 경우
    if not planned_actions:
        return {
            "final_actions": [],
            "resource_calculation": {"warning": "계획된 행동이 없습니다"},
            "messages": [SystemMessage(content="[시스템] 리소스 계산 중 경고: 계획된 행동이 없습니다.")]
        }
    
    # 초기 리소스
    current_ap = current.ap
    current_mov = current.mov
    current_position = current.position
    
    # 최종 행동 및 리소스 계산 결과 리스트
    final_actions = []
    resource_calculations = []
    
    # 각 행동에 대해 리소스 계산 및 검증
    for i, action in enumerate(planned_actions):
        # 스킬 AP 소모량 가져오기
        skill_data = skills.get(action.skill, {})
        skill_ap_cost = skill_data.get('ap', 0)
        
        # 이동 및 행동 비용 계산
        costs = calculate_action_costs(
            current_position=current_position,
            target_position=action.move_to,
            current_ap=current_ap,
            current_mov=current_mov,
            skill_ap_cost=skill_ap_cost
        )
        
        # 계산 결과 저장
        calculation = {
            "action_index": i,
            "from_position": current_position,
            "to_position": action.move_to,
            "skill": action.skill,
            "target_character_id": action.target_character_id,
            "move_cost": costs['move_cost'],
            "ap_cost": skill_ap_cost,
            "remaining_ap": costs['remaining_ap'],
            "remaining_mov": costs['remaining_mov'],
            "can_perform": costs['can_perform']
        }
        
        # 행동 가능 여부 확인
        if not costs['can_perform']:
            # 리소스 부족 원인 파악
            if costs['move_cost'] > current_mov:
                calculation["reason"] = f"이동력 부족: 필요 {costs['move_cost']}, 남은 {current_mov}"
            elif skill_ap_cost > current_ap:
                calculation["reason"] = f"AP 부족: 필요 {skill_ap_cost}, 남은 {current_ap}"
            else:
                calculation["reason"] = "알 수 없는 이유로 행동 불가"
            
            # 이 행동과 이후 행동 제외
            resource_calculations.append(calculation)
            break
        
        # 행동 업데이트 - 계산된 리소스 값으로 조정
        updated_action = CharacterAction(
            move_to=action.move_to,
            skill=action.skill,
            target_character_id=action.target_character_id,
            reason=action.reason,
            remaining_ap=costs['remaining_ap'],
            remaining_mov=costs['remaining_mov']
        )
        
        # 행동 추가
        final_actions.append(updated_action)
        resource_calculations.append(calculation)
        
        # 다음 행동을 위한 상태 업데이트
        current_ap = costs['remaining_ap']
        current_mov = costs['remaining_mov']
        current_position = action.move_to
    
    # 결과 요약 메시지 생성
    summary = create_summary_message(final_actions, planned_actions, resource_calculations)
    
    result = {
        "resource_calculation": {
            "calculations": resource_calculations,
            "original_actions_count": len(planned_actions),
            "final_actions_count": len(final_actions)
        },
        "final_actions": final_actions,
        "messages": [SystemMessage(content=summary)]
    }
    
    return result


def create_summary_message(
    final_actions: List[CharacterAction], 
    planned_actions: List[CharacterAction],
    resource_calculations: List[Dict[str, Any]]
) -> str:
    """리소스 계산 결과 요약 메시지를 생성합니다.
    
    Args:
        final_actions: 최종 행동 목록
        planned_actions: 계획된 행동 목록
        resource_calculations: 리소스 계산 결과
        
    Returns:
        요약 메시지
    """
    if final_actions:
        actions_summary = [
            f"- {i+1}. {a.reason} (남은 AP: {a.remaining_ap}, 남은 MOV: {a.remaining_mov})" 
            for i, a in enumerate(final_actions)
        ]
        
        # 제외된 행동이 있는지 확인
        if len(final_actions) < len(planned_actions):
            excluded_count = len(planned_actions) - len(final_actions)
            excluded_reason = resource_calculations[len(final_actions)].get("reason", "리소스 부족")
            actions_summary.append(f"- {len(final_actions) + 1}. (제외됨) {excluded_reason}")
        
        return f"[시스템] 리소스 계산 완료: {len(final_actions)}개의 행동 실행 가능\n" + "\n".join(actions_summary)
    else:
        return "[시스템] 리소스 계산 결과: 실행 가능한 행동이 없습니다."


def _adjust_move_distance(start_pos, target_pos, available_mov):
    """이동 거리 조정"""
    import math
    
    # 시작 위치와 타겟 위치가 같으면 조정 불필요
    if start_pos == target_pos:
        return start_pos
    
    # 각 축의 거리
    dx = target_pos[0] - start_pos[0]
    dy = target_pos[1] - start_pos[1]
    
    # 맨해튼 거리
    manhattan_dist = abs(dx) + abs(dy)
    
    # 이동 가능한 경우
    if manhattan_dist <= available_mov:
        return target_pos
    
    # 이동 거리 조정
    ratio = available_mov / manhattan_dist
    move_x = round(dx * ratio)
    move_y = round(dy * ratio)
    
    # 조정된 위치
    adjusted_pos = (start_pos[0] + move_x, start_pos[1] + move_y)
    
    # 이동 가능한지 다시 확인
    new_dist = abs(adjusted_pos[0] - start_pos[0]) + abs(adjusted_pos[1] - start_pos[1])
    
    if new_dist > available_mov:
        # 반올림 오차로 여전히 초과하면 더 조정
        if abs(move_x) > abs(move_y):
            move_x = move_x - (1 if move_x > 0 else -1)
        else:
            move_y = move_y - (1 if move_y > 0 else -1)
        
        adjusted_pos = (start_pos[0] + move_x, start_pos[1] + move_y)
    
    return adjusted_pos 