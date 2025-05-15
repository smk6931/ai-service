from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.ai.combat.states import CombatState
from app.utils.loader import traits, prompt_combat_rules
from app.ai.combat.utils import get_current_character
from app.ai.combat.nodes import debug_node


def decide_strategy(state: CombatState) -> Dict[str, Any]:
    """
    전투 전략을 결정하는 노드
    - 상황에 따른 전략 결정
    - 특성(traits)에 기반한 성격 반영 
    - 전투 규칙 고려
    """
    # 디버깅: 입력 데이터 출력
    debug_node("전략 결정 (시작)", input_data=state)
    
    battle_state = state["battle_state"]
    situation_analysis = state["situation_analysis"]
    
    # 현재 캐릭터 정보 확인
    current = get_current_character(battle_state)
    if not current:
        result = {
            "strategy_decision": {"error": "현재 캐릭터를 찾을 수 없습니다"},
            "messages": [SystemMessage(content="[시스템] 전략 결정 중 오류: 현재 캐릭터 정보를 찾을 수 없습니다.")]
        }
        debug_node("전략 결정 (에러)", output_data=result)
        return result
    
    # 캐릭터의 특성(traits) 분석
    character_traits = current.traits
    traits_info = {}
    
    for trait in character_traits:
        if trait in traits:
            traits_info[trait] = traits[trait]
    
    # LLM을 사용하여 전략 결정
    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
        
        strategy_prompt = ChatPromptTemplate.from_messages([
            ("system", prompt_combat_rules + """
당신은 전투 전략 결정을 위한 AI 전문가입니다.
현재 캐릭터의 특성(traits)을 고려하여 가장 적합한 전략을 선택하세요.
응답은 다음 JSON 형식으로만 작성하세요:
{
  "전략_유형": "공격적|방어적|지원형|기동형",
  "우선순위_타겟": "타겟_ID 또는 '없음'",
  "행동_계획": "구체적인 행동 계획 설명",
  "이유": "이 전략을 선택한 이유"
}
"""),
            ("human", f"""
## 현재 상황
- 현재 캐릭터: {current.name} ({current.type})
- 특성: {', '.join(character_traits) if character_traits else '없음'}
- 스킬: {', '.join(current.skills) if current.skills else '없음'}
- 리소스: HP {current.hp}, AP {current.ap}, MOV {current.mov}
- 위치: {current.position}

## 특성 정보
{traits_info}

## 전투 상황
{situation_analysis}

현재 캐릭터 특성과 전투 상황을 고려한 최적의 전략은 무엇입니까?
""")
        ])

        response = llm.invoke(strategy_prompt)
        
        # 응답 처리
        strategy_decision = {
            "strategy_text": response.content,
            "traits": character_traits,
            "traits_info": traits_info
        }
        
        result = {
            "strategy_decision": strategy_decision,
            "messages": [
                SystemMessage(content=f"[시스템] 전략 결정 모듈 실행: {current.name}의 특성 '{', '.join(character_traits) if character_traits else '없음'}' 기반"),
                AIMessage(content=response.content)
            ]
        }
        
        # 디버깅: 출력 데이터 출력
        debug_node("전략 결정 (완료)", output_data=result)
        return result
        
    except Exception as e:
        # 오류 발생 시 기본 전략 결정
        fallback_strategy = {
            "strategy_type": "balanced",
            "priority_target": "nearest_enemy",
            "action_plan": "가장 가까운 적을 찾아 기본 공격 실행",
            "reason": "LLM 전략 결정 실패로 인한 기본 전략 사용"
        }
        
        result = {
            "strategy_decision": {
                "strategy_text": str(fallback_strategy),
                "error": str(e),
                "fallback": True
            },
            "messages": [SystemMessage(content=f"[시스템] 전략 결정 중 오류 발생: {str(e)}. 기본 전략을 사용합니다.")]
        }
        
        # 디버깅: 출력 데이터 출력 (오류)
        debug_node("전략 결정 (폴백)", output_data=result)
        return result 