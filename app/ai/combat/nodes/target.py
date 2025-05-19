from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage
import re

from app.ai.combat.states import CombatState
from app.ai.combat.utils import get_current_character
from app.ai.combat.nodes import debug_node


def select_target(state: CombatState) -> Dict[str, Any]:
    """타겟을 선택하는 노드
    
    전략 결정 결과와 상황 분석 결과를 바탕으로 최적의 타겟을 선택합니다.
    
    Args:
        state: 현재 전투 상태
        
    Returns:
        타겟 선택 결과가 포함된 상태 업데이트
    """
    battle_state = state["battle_state"]
    strategy_decision = state.get("strategy_decision", {})
    situation_analysis = state.get("situation_analysis", {})
    
    # 현재 캐릭터 정보 확인
    current = get_current_character(battle_state)
    if not current:
        return create_error_response("현재 캐릭터를 찾을 수 없습니다")
    
    # 전략 결정이 없거나 오류가 있을 경우 기본 타겟 선택
    if not strategy_decision or "error" in strategy_decision:
        return select_default_target(situation_analysis)
    
    # 전략 텍스트 분석
    strategy_text = strategy_decision.get("strategy_text", "")
    
    # 전략에서 타겟 ID 추출
    target_id = extract_target_from_strategy(strategy_text)
    
    # 타겟 ID가 없으면 전략 유형에 따라 타겟 선택
    if not target_id:
        target_id = select_target_by_strategy(
            strategy_text, 
            situation_analysis.get("target_characters", [])
        )
    
    # 타겟 접근 방식 결정
    approach = determine_approach(situation_analysis, target_id)
    
    # 전략 유형 및 이유 추출
    strategy_type = extract_strategy_type(strategy_text)
    reason = extract_reason(strategy_text)
    
    # 결과 생성
    target_selection = {
        "target_id": target_id,
        "approach": approach,
        "strategy_type": strategy_type,
        "reason": reason[:100] if reason else "전략적 판단"
    }
    
    result = {
        "target_selection": target_selection,
        "messages": [
            SystemMessage(content=f"[시스템] 타겟 선택: {target_id if target_id else '지정된 타겟 없음'} ({approach})")
        ]
    }
    
    return result


def create_error_response(error_message: str) -> Dict[str, Any]:
    """에러 응답을 생성합니다.
    
    Args:
        error_message: 에러 메시지
        
    Returns:
        에러 응답 객체
    """
    return {
        "target_selection": {"error": error_message},
        "messages": [SystemMessage(content=f"[시스템] 타겟 선택 중 오류: {error_message}")]
    }


def select_default_target(situation_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """기본 타겟 선택 로직입니다.
    
    Args:
        situation_analysis: 상황 분석 결과
        
    Returns:
        기본 타겟 선택 결과
    """
    # 상황 분석에서 타겟 정보 추출
    targets = situation_analysis.get("target_characters", [])
    
    target_id = None
    approach = "default"
    
    # 가장 가까운 타겟 선택
    if targets:
        sorted_targets = sorted(targets, key=lambda x: x.get("distance", 999))
        if sorted_targets:
            target_id = sorted_targets[0].get("id")
            approach = determine_approach(situation_analysis, target_id)
    
    target_selection = {
        "target_id": target_id,
        "approach": approach,
        "strategy_type": "balanced",
        "reason": "기본 타겟 선택: 가장 가까운 적 우선"
    }
    
    return {
        "target_selection": target_selection,
        "messages": [SystemMessage(content=f"[시스템] 전략 부재로 기본 타겟 선택: {target_selection['reason']}")]
    }


def extract_target_from_strategy(strategy_text: str) -> Optional[str]:
    """전략 텍스트에서 우선순위 타겟 ID를 추출합니다.
    
    Args:
        strategy_text: 전략 텍스트
        
    Returns:
        타겟 ID 또는 None
    """
    if "우선순위_타겟" not in strategy_text:
        return None
    
    try:
        # "우선순위_타겟": "타겟_ID" 패턴 매칭
        match = re.search(r'\"우선순위_타겟\"\s*:\s*\"([^\"]+)\"', strategy_text)
        if match and match.group(1) != "없음":
            return match.group(1).strip()
    except:
        pass
    
    return None


def select_target_by_strategy(strategy_text: str, target_characters: List[Dict[str, Any]]) -> Optional[str]:
    """전략 유형에 따라 최적의 타겟을 선택합니다.
    
    Args:
        strategy_text: 전략 텍스트
        target_characters: 타겟 캐릭터 목록
        
    Returns:
        선택된 타겟 ID 또는 None
    """
    if not target_characters:
        return None
    
    if "공격적" in strategy_text:
        # 체력이 낮은 적 우선
        sorted_targets = sorted(target_characters, key=lambda x: x.get("hp", 999))
    elif "방어적" in strategy_text:
        # 가까운 적 우선
        sorted_targets = sorted(target_characters, key=lambda x: x.get("distance", 999))
    else:
        # 기본: 거리, 체력 모두 고려
        sorted_targets = sorted(target_characters, 
                              key=lambda x: (x.get("distance", 999), x.get("hp", 999)))
    
    # 최우선 타겟 선택
    if sorted_targets:
        return sorted_targets[0].get("id")
    
    return None


def determine_approach(situation_analysis: Dict[str, Any], target_id: Optional[str]) -> str:
    """타겟 접근 방식을 결정합니다.
    
    Args:
        situation_analysis: 상황 분석 결과
        target_id: 타겟 ID
        
    Returns:
        접근 방식 ("direct", "approach", "no_target")
    """
    if not target_id:
        return "no_target"
    
    # 공격 가능 범위 확인
    targets_in_range = situation_analysis.get("targets_in_range", {})
    
    # 직접 공격 가능한지 확인
    for skill, targets in targets_in_range.items():
        if target_id in targets:
            return "direct"
    
    # 직접 공격 불가능하면 간접 접근
    return "approach"


def extract_strategy_type(strategy_text: str) -> str:
    """전략 유형을 추출합니다.
    
    Args:
        strategy_text: 전략 텍스트
        
    Returns:
        전략 유형 ("aggressive", "defensive", "support", "mobile", "balanced")
    """
    if "공격적" in strategy_text:
        return "aggressive"
    elif "방어적" in strategy_text:
        return "defensive"
    elif "지원형" in strategy_text:
        return "support"
    elif "기동형" in strategy_text:
        return "mobile"
    return "balanced"


def extract_reason(strategy_text: str) -> str:
    """전략 이유를 추출합니다.
    
    Args:
        strategy_text: 전략 텍스트
        
    Returns:
        전략 이유
    """
    try:
        match = re.search(r'\"이유\"\s*:\s*\"([^\"]+)\"', strategy_text)
        if match:
            return match.group(1).strip()
    except:
        pass
        
    return "전략 근거 확인 불가" 