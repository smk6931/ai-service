from typing import Dict, Any
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, END, START

from app.models.combat import BattleStateForAI, BattleActionResponse, CharacterAction
from app.ai.combat.states import CombatState
from app.ai.combat.nodes.situation import analyze_situation
from app.ai.combat.nodes.strategy import decide_strategy
from app.ai.combat.nodes.target import select_target
from app.ai.combat.nodes.action import generate_action
from app.ai.combat.nodes.resource import calculate_resources
from app.ai.combat.nodes import debug_node
from app.ai.combat.utils import get_current_character


def create_response(state: CombatState) -> Dict[str, Any]:
    """최종 응답을 생성합니다.
    
    Args:
        state: 전투 상태
        
    Returns:
        행동 응답 결과
    """
    battle_state = state["battle_state"]
    strategy_decision = state.get("strategy_decision", {})
    final_actions = state.get("final_actions", [])
    
    # 응답 객체 생성 - 행동이 있으면 첫 번째 행동만 사용, 없으면 기본값 생성
    if final_actions:
        action = final_actions[0]
        action.reason = strategy_decision.get("reason", "")
    else:
        # 기본 행동 생성
        current = get_current_character(battle_state)
        action = CharacterAction(
            move_to=current.position if current else (0, 0),
            skill="대기",
            target_character_id=current.id if current else "",
            reason="행동 없음",
            remaining_ap=0,
            remaining_mov=0
        )
    
    response = BattleActionResponse(
        current_character_id=battle_state.current_character_id,
        action=action
    )
    
    # 결과 반환
    result = {
        "response": response,
        "messages": [SystemMessage(content=f"[시스템] 전투 결정 완료: 행동 - {action.skill}")]
    }
    
    return result


def create_combat_graph() -> StateGraph:
    """전투 결정을 위한 LangGraph를 생성합니다.
    
    Returns:
        컴파일된 LangGraph 상태 그래프
    """
    print("전투 그래프 생성 시작")
    
    # 노드 정의 - 각 단계별 처리 함수 매핑
    nodes = {
        "analyze_situation": analyze_situation,  # 1. 상황 분석
        "decide_strategy": decide_strategy,      # 2. 전략 결정
        "select_target": select_target,          # 3. 타겟 선택
        "generate_action": generate_action,      # 4. 행동 생성
        "calculate_resources": calculate_resources,  # 5. 리소스 계산
        "create_response": create_response       # 6. 응답 생성
    }
    
    # 엣지 정의 - 노드 연결 순서
    edges = [
        (START, "analyze_situation"),
        ("analyze_situation", "decide_strategy"),
        ("decide_strategy", "select_target"),
        ("select_target", "generate_action"),
        ("generate_action", "calculate_resources"),
        ("calculate_resources", "create_response"),
        ("create_response", END)
    ]
    
    # 그래프 생성
    combat_graph = StateGraph(CombatState)
    
    # 노드 추가
    for name, func in nodes.items():
        combat_graph.add_node(name, func)
    
    # 엣지 추가
    for start, end in edges:
        combat_graph.add_edge(start, end)
    
    # 그래프 컴파일
    compiled_graph = combat_graph.compile()
    
    print("전투 그래프 생성 완료")
    print("그래프 순서: 상황분석 → 전략결정 → 타겟선택 → 행동생성 → 리소스계산 → 응답생성")
    
    return compiled_graph 