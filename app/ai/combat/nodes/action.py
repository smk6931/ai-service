from typing import Dict, Any, List, Tuple, Optional
import re
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
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


def _generate_action_reason(
    current_character,
    target_character,
    skill_name,
    move_required,
    start_position,
    end_position,
    distance,
    skill_range,
    overall_strategy
):
    """
    LLM을 통해 개별 행동에 대한 이유를 생성하는 함수
    
    Args:
        current_character: 현재 캐릭터 정보
        target_character: 타겟 캐릭터 정보
        skill_name: 사용할 스킬 이름
        move_required: 이동이 필요한지 여부
        start_position: 시작 위치
        end_position: 이동 후 위치
        distance: 타겟과의 거리
        skill_range: 스킬 사거리
        overall_strategy: 전체 전략 텍스트
        
    Returns:
        str: 행동에 대한 이유
    """
    try:
        # LLM 초기화
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, max_tokens=100)
        
        # 시스템 프롬프트
        system_content = """
당신은 전투 AI 시스템의 일부로서 개별 행동의 이유를 설명하는 전문가입니다.
사용자는 특정 행동(이동 및 스킬 사용)에 대한 명확하고 간결한 이유를 원합니다.
전투 상황, 캐릭터 특성, 타겟 정보를 고려하여 이 행동을 선택한 전술적 이유를 한 문장으로 설명하세요.
응답은 30-70자 사이의 간결한 문장으로 작성하고, "~때문입니다"로 끝나도록 합니다.
"""
        
        # 스킬 정보 추출
        skill_info = skills.get(skill_name, {"description": "정보 없음", "ap": "?", "range": "?"})
        
        # 전략 유형 추출
        strategy_type = "균형적"
        if "공격적" in overall_strategy:
            strategy_type = "공격적"
        elif "방어적" in overall_strategy:
            strategy_type = "방어적"
        elif "지원형" in overall_strategy:
            strategy_type = "지원형"
        elif "기동형" in overall_strategy:
            strategy_type = "기동형"
        
        # 휴먼 프롬프트 내용
        human_content = f"""
## 행동 정보
- 캐릭터: {current_character.name} ({current_character.type})
- 특성: {', '.join(current_character.traits) if current_character.traits else '없음'}
- 사용 스킬: {skill_name} (AP: {skill_info.get('ap', '?')}, 범위: {skill_info.get('range', '?')})
- 스킬 설명: {skill_info.get('description', '정보 없음')}
- 이동 여부: {'필요' if move_required else '불필요'} (시작: {start_position}, 도착: {end_position})
- 타겟: ID {target_character.id}, {target_character.name}, HP {target_character.hp}
- 타겟과의 거리: {distance} (스킬 범위: {skill_range})

## 전체 전략 방향
- 전략 유형: {strategy_type}
- 전략 설명: {overall_strategy[:100]}...

위 정보를 바탕으로 이 행동을 선택한 전술적 이유를 간결하게 설명해주세요.
"""
        
        # 메시지 구성
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_content),
            HumanMessage(content=human_content)
        ])
        
        # LLM 호출
        messages = prompt.format_messages()
        response = llm.invoke(messages)
        
        return response.content.strip()
        
    except Exception as e:
        # LLM 호출 중 오류 발생 시 기본 이유 반환
        return f"{skill_name} 스킬이 현재 상황에 적합하기 때문입니다"


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
    
    # 전략 이유 추출 (전체 전략에서 사용)
    strategy_text = strategy_decision.get("strategy_text", "")
    overall_strategy = strategy_text
    
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
    
    # 타겟 위치 및 정보 확인
    target_character = None
    target_position = None
    for character in battle_state.characters:
        if character.id == target_id:
            target_character = character
            target_position = character.position
            break
            
    if not target_position or not target_character:
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
        move_required = False
        
        # 타겟이 사거리 밖에 있으면 이동해야 함
        if distance_to_target > skill_range:
            move_required = True
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
        
        # LLM을 통해 개별 행동에 대한 이유 생성
        action_reason = _generate_action_reason(
            current_character=current,
            target_character=target_character,
            skill_name=skill_name,
            move_required=(current_position != optimal_position),
            start_position=current_position,
            end_position=optimal_position,
            distance=distance_to_target,
            skill_range=skill_range,
            overall_strategy=overall_strategy
        )
        
        # 행동 생성 - 개별 행동 이유를 사용
        reason = f"{action_description} - {action_reason}"
        
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