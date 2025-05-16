import json
from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from app.ai.combat.states import CombatState
from app.models.combat import CharacterForAI, StrategyDecision
from app.utils.loader import traits, prompt_combat_rules
from app.ai.combat.utils import get_current_character
from app.ai.combat.nodes import debug_node


def decide_strategy(state: CombatState) -> Dict[str, Any]:
    """전투 전략을 결정하는 노드
    
    상황에 따른 전략을 결정하고, 캐릭터 특성(traits) 정보를 고려합니다.
    
    Args:
        state: 현재 전투 상태
        
    Returns:
        전략 결정 결과가 포함된 상태 업데이트
    """
    # 입력값 디버깅
    debug_node("decide_strategy", input_data=state)
    
    try:
        battle_state = state["battle_state"]
        situation_analysis = state.get("situation_analysis", {})
        
        # 현재 캐릭터 정보 확인
        current = get_current_character(battle_state)
        if not current:
            # 현재 캐릭터가 없는 경우 에러 반환
            result = {
                "strategy_decision": {"error": "현재 캐릭터를 찾을 수 없습니다"},
                "messages": [SystemMessage(content="[시스템] 전략 결정 중 오류: 현재 캐릭터를 찾을 수 없습니다")]
            }
            # 에러 출력값 디버깅
            debug_node("decide_strategy", output_data=result, error=True)
            return result
        
        # 상황 분석 및 특성 정보 준비
        try:
            situation_text = json.dumps(situation_analysis, ensure_ascii=False, indent=2)
        except:
            situation_text = str(situation_analysis)
            
        traits_info = get_traits_info(current)
        try:
            traits_info_text = json.dumps(traits_info, ensure_ascii=False, indent=2)
        except:
            traits_info_text = str(traits_info)
        
        # Pydantic 모델을 활용한 출력 파서 설정
        parser = PydanticOutputParser(pydantic_object=StrategyDecision)
        
        # LLM을 통한 전략 결정
        strategy_response = get_llm_strategy_decision(
            current, traits_info_text, situation_text, parser
        )
        
        # 요약 메시지 생성
        traits_text = ', '.join(current.traits) if current.traits else '없음'
        summary_message = f"[시스템] 전략 결정 모듈 실행: {current.name}의 특성 '{traits_text}' 기반"
        
        # Pydantic 객체를 딕셔너리로 변환
        strategy_dict = strategy_response.dict()
        strategy_text = strategy_response.json()
        
        # 응답 처리
        strategy_decision = {
            "strategy_dict": strategy_dict,
            "strategy_text": strategy_text,
            "traits": current.traits or [],
            "traits_info": traits_info
        }
        
        result = {
            "strategy_decision": strategy_decision,
            "messages": [
                SystemMessage(content=summary_message),
                AIMessage(content=strategy_text)
            ]
        }
        
        # 출력값 디버깅
        debug_node("decide_strategy", output_data=result)
        
        return result
        
    except Exception as e:
        error_message = str(e)
        fallback_strategy = StrategyDecision(
            strategy_type="공격적",
            priority_target="nearest_enemy",
            action_plan="가장 가까운 적을 찾아 기본 공격 실행",
            reason="LLM 전략 결정 실패로 인한 기본 전략 사용"
        )
        
        # Pydantic 객체를 딕셔너리로 변환
        fallback_dict = fallback_strategy.dict()
        fallback_text = fallback_strategy.json()
        
        result = {
            "strategy_decision": {
                "strategy_dict": fallback_dict,
                "strategy_text": fallback_text,
                "error": error_message,
                "fallback": True
            },
            "messages": [SystemMessage(content=f"[시스템] 전략 결정 중 오류 발생: {error_message}. 기본 전략을 사용합니다.")]
        }
        
        # 에러 출력값 디버깅
        debug_node("decide_strategy", output_data=result, error=True)
        return result


def get_traits_info(character: CharacterForAI) -> Dict[str, Any]:
    """캐릭터의 특성 정보를 가져옵니다.
    
    Args:
        character: 캐릭터 객체
        
    Returns:
        특성 정보 딕셔너리
    """
    character_traits = character.traits or []
    traits_info = {}
    
    for trait in character_traits:
        if trait in traits:
            traits_info[trait] = traits[trait]
    
    return traits_info


def get_llm_strategy_decision(
    character: CharacterForAI, 
    traits_info_text: str, 
    situation_text: str,
    parser: PydanticOutputParser
) -> StrategyDecision:
    """LLM을 사용해서 전략 결정을 수행합니다.
    
    Args:
        character: 캐릭터 객체
        traits_info_text: 특성 정보 텍스트
        situation_text: 상황 분석 텍스트
        parser: 출력 파서
        
    Returns:
        LLM이 생성한 전략 결정 응답
    """
    # 시스템 프롬프트 구성
    system_content = prompt_combat_rules + """
당신은 전투 전략 결정을 위한 AI 전문가입니다.
현재 캐릭터의 특성(traits)을 고려하여 가장 적합한 전략을 선택하세요.
"""
    
    # 휴먼 프롬프트 구성 
    human_content = f"""
## 현재 상황
- 현재 캐릭터: {character.name} ({character.type})
- 특성: {', '.join(character.traits or ['없음'])}
- 스킬: {', '.join(character.skills or ['없음'])}
- 리소스: HP {character.hp}, AP {character.ap}, MOV {character.mov}
- 위치: {character.position}

## 특성 정보
{traits_info_text}

## 전투 상황
{situation_text}

현재 캐릭터 특성과 전투 상황을 고려한 최적의 전략은 무엇입니까?

{parser.get_format_instructions()}
"""

    # LLM 호출
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    strategy_prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_content),
        HumanMessage(content=human_content)
    ])

    chain = strategy_prompt | llm | parser
    return chain.invoke({}) 
