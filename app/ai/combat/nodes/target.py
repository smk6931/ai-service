from typing import Dict, Any, List, Tuple
from langchain_core.messages import SystemMessage
import json
from app.ai.combat.states import CombatState
from app.ai.combat.utils import get_current_character, calculate_manhattan_distance
from app.utils.loader import skills
from app.ai.combat.nodes import debug_node


def select_target(state: CombatState) -> Dict[str, Any]:
    """
    타겟 선택 노드
    - 전략에 따른 최적의 타겟 선택
    - 거리, HP 등을 고려한 우선순위 결정
    """
    # 디버깅: 입력 데이터 출력
    debug_node("타겟 선택 (시작)", input_data=state)
    
    battle_state = state["battle_state"]
    situation_analysis = state["situation_analysis"]
    strategy_decision = state["strategy_decision"]
    
    # 현재 캐릭터 정보 확인
    current = get_current_character(battle_state)
    if not current:
        result = {
            "target_selection": {"error": "현재 캐릭터를 찾을 수 없습니다"},
            "messages": [SystemMessage(content="[시스템] 타겟 선택 중 오류: 현재 캐릭터 정보를 찾을 수 없습니다.")]
        }
        debug_node("타겟 선택 (에러)", output_data=result)
        return result
    
    # 타겟 캐릭터 목록 확인
    target_type = "player" if current.type == "monster" else "monster"
    target_characters = [c for c in battle_state.characters if c.type == target_type]
    
    if not target_characters:
        result = {
            "target_selection": {"error": "타겟 캐릭터가 없습니다"},
            "messages": [SystemMessage(content="[시스템] 타겟 선택 중 오류: 타겟 캐릭터가 없습니다.")]
        }
        debug_node("타겟 선택 (에러)", output_data=result)
        return result
    
    # 전략에서 우선순위 타겟 정보 추출 시도
    priority_target_id = None
    
    try:
        # JSON 형식으로 파싱 시도
        if isinstance(strategy_decision.get("strategy_text"), str):
            strategy_text = strategy_decision["strategy_text"]
            strategy_json = json.loads(strategy_text)
            priority_target_id = strategy_json.get("우선순위_타겟")
            
            # 우선순위 타겟이 "없음"이거나 존재하지 않는 경우 None으로 설정
            if priority_target_id == "없음" or not any(t.id == priority_target_id for t in target_characters):
                priority_target_id = None
                
    except (KeyError, json.JSONDecodeError, TypeError):
        # JSON 파싱 실패 시 무시하고 계속 진행
        pass
    
    # 타겟 점수 계산
    target_scores = []
    for target in target_characters:
        # 기본 점수 = 100에서 시작
        score = 100
        
        # 거리에 따른 페널티 (거리가 멀수록 점수 감소)
        distance = calculate_manhattan_distance(current.position, target.position)
        score -= distance * 10  # 거리당 10점 감소
        
        # 낮은 HP의 적을 우선 타겟팅 (HP가 낮을수록 점수 증가)
        hp_factor = 100 - min(100, target.hp)  # HP가 0에 가까울수록 높은 점수
        score += hp_factor * 0.5
        
        # 우선순위 타겟인 경우 보너스 점수
        if priority_target_id and target.id == priority_target_id:
            score += 200  # 우선순위 타겟에 큰 보너스
        
        target_scores.append((target, score))
    
    # 점수에 따라 정렬 (높은 점수 우선)
    target_scores.sort(key=lambda x: x[1], reverse=True)
    
    # 최종 타겟 선택
    selected_targets = []
    for target, score in target_scores:
        selected_targets.append({
            "id": target.id,
            "name": target.name,
            "position": target.position,
            "hp": target.hp,
            "distance": calculate_manhattan_distance(current.position, target.position),
            "score": score
        })
    
    # 각 스킬별 최적 타겟 선택
    skill_targets = {}
    for skill_name in current.skills:
        # 스킬 정보
        skill_data = skills.get(skill_name, {})
        skill_range = skill_data.get('range', 1)
        
        # 사거리 내 대상 필터링
        in_range_targets = [t for t in target_scores 
                          if calculate_manhattan_distance(current.position, t[0].position) <= skill_range]
        
        if in_range_targets:
            # 점수 순 정렬
            best_target = in_range_targets[0][0]
            skill_targets[skill_name] = {
                "id": best_target.id,
                "name": best_target.name,
                "position": best_target.position,
                "distance": calculate_manhattan_distance(current.position, best_target.position)
            }
    
    target_selection = {
        "selected_targets": selected_targets,
        "skill_targets": skill_targets,
        "priority_target_id": priority_target_id
    }
    
    # 메시지 생성
    summary = f"[시스템] 타겟 선택 완료: "
    if selected_targets:
        summary += f"최우선 타겟은 {selected_targets[0]['name']}(ID: {selected_targets[0]['id']}, 점수: {selected_targets[0]['score']:.1f})"
    else:
        summary += "선택 가능한 타겟이 없습니다."
    
    result = {
        "target_selection": target_selection,
        "messages": [SystemMessage(content=summary)]
    }
    
    # 디버깅: 출력 데이터 출력
    debug_node("타겟 선택 (완료)", output_data=result)
    
    return result 