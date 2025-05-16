from typing import Annotated, Dict, List, Optional, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage

from app.models.combat import BattleStateForAI, BattleActionResponse, CharacterAction


class CombatState(TypedDict):
    """전투 그래프의 상태를 정의합니다"""
    # 원본 전투 상태 데이터
    battle_state: BattleStateForAI
    
    # 현재 분석된 상황
    situation_analysis: Dict[str, Any]
    
    # 전략 결정 결과
    strategy_decision: Dict[str, Any]
    
    # 타겟 선택 결과
    target_selection: Dict[str, Any]
    
    # 행동 계획
    planned_actions: List[CharacterAction]
    
    # 리소스 계산 결과
    resource_calculation: Dict[str, Any]
    
    # 최종 행동 결정
    final_actions: List[CharacterAction]
    
    # 판단 과정과 결과에 대한 설명 메시지
    messages: Annotated[List[AnyMessage], add_messages]
    
    # 최종 응답
    response: Optional[BattleActionResponse] 