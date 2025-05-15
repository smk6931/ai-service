from typing import Dict, Any, List, Tuple
from langchain_core.messages import SystemMessage, AIMessage
import json
from app.ai.combat.states import CombatState
from app.ai.combat.utils import get_current_character, calculate_manhattan_distance
from app.utils.loader import skills
from app.ai.combat.nodes import debug_node


def select_target(state: CombatState) -> Dict[str, Any]:
    """
    타겟을 선택하는 노드
    - 전략과 상황에 따른 최적의 타겟 선택
    - 타겟 접근 방법 결정 (직접/간접)
    """
    # 입력 데이터 디버깅 출력 제거
    
    battle_state = state["battle_state"]
    strategy_decision = state.get("strategy_decision", {})
    situation_analysis = state.get("situation_analysis", {})
    
    # 현재 캐릭터 정보 확인
    current = get_current_character(battle_state)
    if not current:
        result = {
            "target_selection": {"error": "현재 캐릭터를 찾을 수 없습니다"},
            "messages": [SystemMessage(content="[시스템] 타겟 선택 중 오류: 현재 캐릭터 정보를 찾을 수 없습니다.")]
        }
        debug_node("타겟 선택 (에러)", input_data=state, output_data=result, error=True)
        return result
    
    # 전략 결정이 없거나 오류가 있을 경우
    if not strategy_decision or "error" in strategy_decision:
        # 기본 전략 결정 사용
        target_selection = _default_target_selection(battle_state, situation_analysis)
        result = {
            "target_selection": target_selection,
            "messages": [SystemMessage(content="[시스템] 전략 부재로 기본 타겟 선택: " + target_selection["reason"])]
        }
        debug_node("타겟 선택 (기본)", input_data=state, output_data=result, error=True)
        return result
    
    # 전략 텍스트 분석
    strategy_text = strategy_decision.get("strategy_text", "")
    
    # 선택된 타겟 ID 추출 시도
    target_id = None
    
    # 전략에서 타겟 ID 추출 시도
    if "우선순위_타겟" in strategy_text:
        try:
            import re
            # "우선순위_타겟": "타겟_ID" 패턴 매칭
            match = re.search(r'\"우선순위_타겟\"\s*:\s*\"([^\"]+)\"', strategy_text)
            if match and match.group(1) != "없음":
                target_id = match.group(1).strip()
        except:
            pass
    
    # 타겟 ID가 없으면 기본 타겟 선택 로직 사용
    if not target_id:
        target_characters = situation_analysis.get("target_characters", [])
        if target_characters:
            # 전략에 따른 타겟 선택 가중치 적용
            if "공격적" in strategy_text:
                # 체력이 낮은 적 우선
                sorted_targets = sorted(target_characters, key=lambda x: x.get("hp", 999))
            elif "방어적" in strategy_text:
                # 가까운 적 우선
                sorted_targets = sorted(target_characters, key=lambda x: x.get("distance", 999))
            elif "지원형" in strategy_text:
                # 아군 대상 (아직 미구현, 지금은 가장 가까운 대상)
                sorted_targets = sorted(target_characters, key=lambda x: x.get("distance", 999))
            else:
                # 기본: 거리, 체력 모두 고려
                sorted_targets = sorted(target_characters, 
                                         key=lambda x: (x.get("distance", 999), x.get("hp", 999)))
            
            # 최우선 타겟 선택
            if sorted_targets:
                target_id = sorted_targets[0].get("id")
    
    # 결과 생성
    target_selection = {
        "target_id": target_id,
        "approach": _determine_approach(situation_analysis, target_id),
        "strategy_type": _extract_strategy_type(strategy_text),
        "reason": f"전략적 판단: {_extract_reason(strategy_text)[:100]}..." if len(_extract_reason(strategy_text)) > 100 else _extract_reason(strategy_text)
    }
    
    result = {
        "target_selection": target_selection,
        "messages": [
            SystemMessage(content=f"[시스템] 타겟 선택: {target_id if target_id else '지정된 타겟 없음'} ({target_selection['approach']})"),
            SystemMessage(content=f"[시스템] 접근 방식: {target_selection['approach']}")
        ]
    }
    
    # 디버깅 출력 제거
    return result


def _default_target_selection(battle_state, situation_analysis):
    """기본 타겟 선택 로직"""
    targets = []
    
    # 타겟 유형 결정
    current = get_current_character(battle_state)
    if current:
        target_type = "player" if current.type == "monster" else "monster"
        # 상황 분석에서 타겟 정보 추출
        targets = situation_analysis.get("target_characters", [])
    
    target_id = None
    approach = "default"
    
    # 가장 가까운 타겟 선택
    if targets:
        # 거리가 가장 가까운 타겟 선택
        sorted_targets = sorted(targets, key=lambda x: x.get("distance", 999))
        if sorted_targets:
            target_id = sorted_targets[0].get("id")
            # 접근 방식 결정
            approach = _determine_approach(situation_analysis, target_id)
    
    return {
        "target_id": target_id,
        "approach": approach,
        "strategy_type": "balanced",
        "reason": "기본 타겟 선택: 가장 가까운 적 우선"
    }


def _determine_approach(situation_analysis, target_id):
    """타겟 접근 방식 결정"""
    # 공격 가능 범위 확인
    targets_in_range = situation_analysis.get("targets_in_range", {})
    
    # 직접 공격 가능한지 확인
    for skill, targets in targets_in_range.items():
        if target_id in targets:
            return "direct"
    
    # 직접 공격 불가능하면 간접 접근
    return "approach"


def _extract_strategy_type(strategy_text):
    """전략 유형 추출"""
    if "공격적" in strategy_text:
        return "aggressive"
    elif "방어적" in strategy_text:
        return "defensive"
    elif "지원형" in strategy_text:
        return "support"
    elif "기동형" in strategy_text:
        return "mobile"
    return "balanced"


def _extract_reason(strategy_text):
    """전략 이유 추출"""
    import re
    
    try:
        match = re.search(r'\"이유\"\s*:\s*\"([^\"]+)\"', strategy_text)
        if match:
            return match.group(1).strip()
    except:
        pass
        
    return "전략 근거 확인 불가" 