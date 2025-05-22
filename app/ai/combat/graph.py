from typing import List, Dict, Any, Optional
from langchain.schema import BaseMessage
from langgraph.graph import StateGraph, END
from app.ai.combat.states import LangGraphBattleState
from app.ai.combat.nodes import (
    analyze_situation,
    decide_strategy,
    plan_attack,
    plan_flee,
    generate_dialogue,
    create_response
)

def should_route_to_attack_or_flee(state: LangGraphBattleState) -> str:
    """전략 타입에 따라 공격 또는 도망 노드로 라우팅"""
    # 구조화된 전략 정보를 기반으로 라우팅 결정
    if state.strategy_info:
        strategy_type = state.strategy_info.type
        if strategy_type in ["방어 우선", "도망 우선"]:
            return "flee"
        else:
            return "attack"
    # else:
    #     # 구조화된 정보가 없는 경우 텍스트 기반으로 판단 (후방 호환성)
    #     strategy_text = state.strategy.lower() if state.strategy else ""
    #     if "도망" in strategy_text or "후퇴" in strategy_text or "방어" in strategy_text:
    #         return "flee"
    #     else:
    #         # 기본값은 공격
    #         return "attack"

def create_combat_graph() -> StateGraph:
    """전투 AI 그래프 생성"""
    # 상태 그래프 생성
    workflow = StateGraph(LangGraphBattleState)
    
    # 노드 추가
    workflow.add_node("analyze_situation", analyze_situation)
    workflow.add_node("decide_strategy", decide_strategy)
    workflow.add_node("plan_attack", plan_attack)
    workflow.add_node("plan_flee", plan_flee)
    workflow.add_node("generate_dialogue", generate_dialogue)
    workflow.add_node("create_response", create_response)
    
    # 엣지 연결 (기본 흐름)
    workflow.add_edge("analyze_situation", "decide_strategy")
    
    # 전략에 따른 분기
    workflow.add_conditional_edges(
        "decide_strategy",
        should_route_to_attack_or_flee,
        {
            "attack": "plan_attack",
            "flee": "plan_flee"
        }
    )
    
    # 행동 계획 수립 후 대사 생성
    workflow.add_edge("plan_attack", "generate_dialogue")
    workflow.add_edge("plan_flee", "generate_dialogue")
    
    workflow.add_edge("generate_dialogue", "create_response")
    workflow.add_edge("create_response", END)
    
    # 시작 노드 설정
    workflow.set_entry_point("analyze_situation")
    
    return workflow

async def run_graph(state: LangGraphBattleState) -> LangGraphBattleState:
    """전투 AI 그래프 실행"""
    try:
        # 그래프 생성
        graph = create_combat_graph()
        
        # 그래프 컴파일
        compiled_graph = graph.compile()
        
        # 비동기 실행 (LangGraph 1.0.0+)
        result = await compiled_graph.ainvoke(state)
        
        # 최종 상태 반환
        return result
    except Exception as e:
        print(f"그래프 실행 오류: {str(e)}")
        # 오류 발생 시 원래 상태 반환
        return state
