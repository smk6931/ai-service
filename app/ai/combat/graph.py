from typing import Dict, Any
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, END, START

from app.models.combat import BattleStateForAI, BattleActionResponse
from app.ai.combat.states import CombatState
from app.ai.combat.nodes.situation import analyze_situation
from app.ai.combat.nodes.strategy import decide_strategy
from app.ai.combat.nodes.target import select_target
from app.ai.combat.nodes.action import generate_action
from app.ai.combat.nodes.resource import calculate_resources
from app.ai.combat.nodes import debug_node


def create_response(state: CombatState) -> Dict[str, Any]:
    """
    최종 응답 생성 노드
    - 모든 단계가 완료된 후 최종 응답 형식 생성
    """
    # 디버깅: 입력 데이터 출력
    debug_node("응답 생성 (시작)", input_data=state)
    
    battle_state = state["battle_state"]
    final_actions = state.get("final_actions", [])
    
    # BattleActionResponse 생성
    response = BattleActionResponse(
        current_character_id=battle_state.current_character_id,
        actions=final_actions
    )
    
    result = {
        "response": response,
        "messages": [SystemMessage(content=f"[시스템] 전투 결정 완료: {len(final_actions)}개의 행동")]
    }
    
    # 디버깅: 최종 응답 출력
    debug_node("응답 생성 (완료)", output_data=result)
    
    return result


def create_combat_graph() -> StateGraph:
    """
    전투 결정을 위한 LangGraph 생성
    - 전체 패턴: 상황분석 → 전략결정 → 타겟선택 → 행동생성 → 리소스계산 → 응답생성
    """
    print("\n" + "=" * 50)
    print("전투 그래프 생성 시작")
    print("=" * 50)
    
    # 상태 그래프 생성
    combat_graph = StateGraph(CombatState)
    
    # 노드 추가
    combat_graph.add_node("analyze_situation", analyze_situation)
    combat_graph.add_node("decide_strategy", decide_strategy)
    combat_graph.add_node("select_target", select_target)
    combat_graph.add_node("generate_action", generate_action)
    combat_graph.add_node("calculate_resources", calculate_resources)
    combat_graph.add_node("create_response", create_response)
    
    # 노드 간 연결
    combat_graph.add_edge(START, "analyze_situation")
    combat_graph.add_edge("analyze_situation", "decide_strategy")
    combat_graph.add_edge("decide_strategy", "select_target")
    combat_graph.add_edge("select_target", "generate_action")
    combat_graph.add_edge("generate_action", "calculate_resources")
    combat_graph.add_edge("calculate_resources", "create_response")
    combat_graph.add_edge("create_response", END)
    
    # 그래프 컴파일
    compiled_graph = combat_graph.compile()
    
    print("\n" + "=" * 50)
    print("전투 그래프 생성 완료")
    print("그래프 순서: 상황분석 → 전략결정 → 타겟선택 → 행동생성 → 리소스계산 → 응답생성")
    print("=" * 50 + "\n")
    
    return compiled_graph 