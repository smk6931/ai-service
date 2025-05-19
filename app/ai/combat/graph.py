from typing import List, Dict, Any, Optional
from langchain.schema import BaseMessage
from langgraph.graph import StateGraph, END
from app.ai.combat.states import LangGraphBattleState
from app.ai.combat.nodes import (
    analyze_situation,
    decide_strategy,
    plan_action,
    generate_dialogue,
    create_response
)

def should_skip_dialogue(state: LangGraphBattleState) -> str:
    """대사 생성 여부 결정 함수"""
    # 대기 상태인 경우 대사 생성 스킵
    if (state.action_plan and state.action_plan.skill == "대기" and 
        state.action_plan.target_character_id == state.current_character_id):
        return "skip_dialogue"
    return "generate_dialogue"

def create_combat_graph() -> StateGraph:
    """전투 AI 그래프 생성"""
    # 상태 그래프 생성
    workflow = StateGraph(LangGraphBattleState)
    
    # 노드 추가
    workflow.add_node("analyze_situation", analyze_situation)
    workflow.add_node("decide_strategy", decide_strategy)
    workflow.add_node("plan_action", plan_action)
    workflow.add_node("generate_dialogue", generate_dialogue)
    workflow.add_node("create_response", create_response)
    
    # 엣지 연결 (기본 흐름)
    workflow.add_edge("analyze_situation", "decide_strategy")
    workflow.add_edge("decide_strategy", "plan_action")
    
    # 조건부 분기: 대사 생성 스킵 여부
    workflow.add_conditional_edges(
        "plan_action",
        should_skip_dialogue,
        {
            "generate_dialogue": "generate_dialogue",
            "skip_dialogue": "create_response"
        }
    )
    
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
