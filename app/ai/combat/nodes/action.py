from typing import Dict, Any, List, Tuple, Optional
import re
from langchain_core.messages import SystemMessage
from app.ai.combat.states import CombatState
from app.ai.combat.utils import get_current_character, calculate_manhattan_distance, calculate_movable_positions
from app.models.combat import CharacterAction
from app.utils.loader import skills
from app.ai.combat.nodes import debug_node


def _extract_reason(strategy_text):
    """전략 이유 추출"""
    try:
        match = re.search(r'\"이유\"\s*:\s*\"([^\"]+)\"', strategy_text)
        if match:
            return match.group(1).strip()
    except:
        pass
        
    return "전략 근거 확인 불가"


def generate_action(state: CombatState) -> Dict[str, Any]:
    """
    행동 생성 노드
    - 이동 및 스킬 사용 계획 수립
    - 현재 리소스 고려 (AP, MOV)
    - 타겟과의 거리 및 스킬 사거리 고려
    """
    
    battle_state = state["battle_state"]
    situation_analysis = state["situation_analysis"]
    strategy_decision = state["strategy_decision"]
    target_selection = state["target_selection"]
    
    # 현재 캐릭터 정보 확인
    current = get_current_character(battle_state)
    if not current:
        result = {
            "planned_actions": [],
            "messages": [SystemMessage(content="[시스템] 행동 생성 중 오류: 현재 캐릭터 정보를 찾을 수 없습니다.")]
        }
        debug_node("행동 생성 (에러)", input_data=state, output_data=result, error=True)
        return result
    
    # 타겟 정보 확인
    target_id = target_selection.get("target_id")
    approach = target_selection.get("approach", "direct")
    
    if not target_id:
        result = {
            "planned_actions": [],
            "messages": [SystemMessage(content="[시스템] 행동 생성 중 오류: 선택된 타겟이 없습니다.")]
        }
        debug_node("행동 생성 (에러)", input_data=state, output_data=result, error=True)
        return result
    
    # 전략 이유 추출
    strategy_text = strategy_decision.get("strategy_text", "")
    strategy_reason = _extract_reason(strategy_text)
    
    # 이동 가능한 위치 계산
    movable_positions = calculate_movable_positions(battle_state)
    
    # AP 및 MOV 리소스
    current_ap = current.ap
    current_mov = current.mov
    current_position = current.position
    
    # 행동 리스트 생성
    planned_actions = []
    remaining_ap = current_ap
    remaining_mov = current_mov
    
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
        result = {
            "planned_actions": [],
            "messages": [SystemMessage(content="[시스템] 행동 생성 중 오류: 사용 가능한 스킬이 없습니다.")]
        }
        debug_node("행동 생성 (에러)", input_data=state, output_data=result, error=True)
        return result
    
    # 타겟 위치 확인
    target_position = None
    for character in battle_state.characters:
        if character.id == target_id:
            target_position = character.position
            break
            
    if not target_position:
        result = {
            "planned_actions": [],
            "messages": [SystemMessage(content=f"[시스템] 행동 생성 중 오류: 타겟 ID {target_id}의 위치를 찾을 수 없습니다.")]
        }
        debug_node("행동 생성 (에러)", input_data=state, output_data=result, error=True)
        return result
    
    # 행동 계획 (최대 3개의 행동 시도)
    for attempt in range(min(3, len(available_skills))):
        if not available_skills or remaining_ap <= 0 or remaining_mov <= 0:
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
        
        # 타겟이 사거리 밖에 있으면 이동해야 함
        if distance_to_target > skill_range:
            # 최소한의 이동으로 사거리 내로 들어갈 수 있는 위치 찾기
            best_distance = float('inf')
            for pos in movable_positions:
                move_distance = calculate_manhattan_distance(current_position, pos)
                if move_distance <= remaining_mov:  # 이동 가능한 거리 내
                    distance_after_move = calculate_manhattan_distance(pos, target_position)
                    if distance_after_move <= skill_range:  # 이동 후 사거리 내
                        total_distance = move_distance + distance_after_move  # 총 이동 거리 + 타겟까지 거리
                        if total_distance < best_distance:
                            best_distance = total_distance
                            optimal_position = pos
            
            # 이동할 위치를 찾지 못했으면 다음 행동으로
            if optimal_position == current_position and distance_to_target > skill_range:
                continue
        
        # 이동 비용 계산
        move_cost = calculate_manhattan_distance(current_position, optimal_position)
        
        # 리소스 소비 계산
        if move_cost > remaining_mov:
            continue  # 이동력 부족하면 다음 행동으로
            
        # AP 소비 계산
        if skill_ap > remaining_ap:
            continue  # AP 부족하면 다음 행동으로
        
        # 행동 설명 생성 (이동 여부에 따라 다름)
        action_description = f"{target_id}에게 {skill_name} 스킬 사용"
        if current_position != optimal_position:
            action_description = f"{optimal_position}으로 이동 후 {target_id}에게 {skill_name} 스킬 사용"
        
        # 행동 생성 - 전략 이유와 행동 설명을 조합
        reason = f"{action_description} - {strategy_reason}"
        
        action = CharacterAction(
            move_to=optimal_position,
            skill=skill_name,
            target_character_id=target_id,
            reason=reason,
            remaining_ap=remaining_ap - skill_ap,
            remaining_mov=remaining_mov - move_cost
        )
        
        # 행동 추가
        planned_actions.append(action)
        
        # 남은 리소스 업데이트
        remaining_ap -= skill_ap
        remaining_mov -= move_cost
        current_position = optimal_position  # 다음 행동의 시작 위치 업데이트
    
    # 결과 요약 메시지 생성
    if planned_actions:
        actions_summary = "\n".join([f"- {i+1}. {a.reason} (남은 AP: {a.remaining_ap}, 남은 MOV: {a.remaining_mov})" 
                                   for i, a in enumerate(planned_actions)])
        summary = f"[시스템] 행동 계획 생성 완료: {len(planned_actions)}개의 행동\n{actions_summary}"
    else:
        summary = "[시스템] 행동 계획 생성 결과: 실행 가능한 행동이 없습니다."
    
    result = {
        "planned_actions": planned_actions,
        "messages": [SystemMessage(content=summary)]
    }
    
    return result 