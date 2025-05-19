from typing import Dict, List, Tuple, Optional
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

from app.ai.combat.states import LangGraphBattleState, Character, ActionPlan
from app.utils.combat import calculate_manhattan_distance
from dotenv import load_dotenv
# 환경 변수 로드
load_dotenv()

# LLM 인스턴스 생성
# llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.5)
llm = ChatOpenAI(model_name="gpt-4.1-nano", temperature=0.5)


def analyze_situation(state: LangGraphBattleState) -> LangGraphBattleState:
    """
    상황 분석 노드: 현재 전투 상황을 분석하고 캐릭터 간 거리, 위험도 등 계산
    """
    print("[상황 분석 노드] 시작")
    # 현재 캐릭터 찾기
    current_character = next((c for c in state.characters if c.id == state.current_character_id), None)
    if not current_character:
        raise ValueError(f"현재 캐릭터 ID '{state.current_character_id}'를 찾을 수 없습니다.")
    
    # 자원 정보 계산 (HP 비율, AP, MOV 등)
    resource_info = {
        "hp_ratio": current_character.hp / 100,  # 예시: 최대 HP가 100이라고 가정
        "ap": current_character.ap,
        "mov": current_character.mov
    }
    
    # 전투 요약 생성 (최근 로그 기반)
    battle_summary = "현재 전투 상황: "
    if state.battle_log:
        recent_logs = state.battle_log[-3:] if len(state.battle_log) > 3 else state.battle_log
        battle_summary += " ".join(recent_logs)
    else:
        battle_summary += "전투 시작 단계"
    
    # 상태 업데이트
    state.resource_info = resource_info
    state.battle_summary = battle_summary
    
    # 트레이스 기록 시작
    state.trace = ["상황 분석 완료"]
    print("[상황 분석 노드] 상태\n", state)
    
    return state

def decide_strategy(state: LangGraphBattleState) -> LangGraphBattleState:
    """
    전략 결정 노드: 캐릭터 특성과 상황을 기반으로 행동 전략 결정 (LLM 호출)
    """
    print("[전략 결정 노드] 시작")
    # 현재 캐릭터 찾기
    current_character = next((c for c in state.characters if c.id == state.current_character_id), None)
    
    # 전략 결정을 위한 프롬프트 구성
    prompt = f"""
    당신은 '{current_character.name}'이라는 {current_character.type} 캐릭터입니다.
    캐릭터 특성: {', '.join(current_character.traits)}
    현재 HP: {current_character.hp}, AP: {current_character.ap}, MOV: {current_character.mov}
    상태 이상: {', '.join(current_character.status_effects) if current_character.status_effects else '없음'}
    
    전투 환경:
    - 지형: {state.terrain}
    - 날씨: {state.weather}
    
    전투 상황:
    {state.battle_summary}
    
    다음 중 하나의 전략을 선택하고 그 이유를 간략히 설명하세요:
    1. 공격 우선 (근접한 적에게 최대 피해)
    2. 처치 우선 (가장 약한 적에게 최대 피해)
    3. 방어 우선 (회피 및 생존 중심)
    4. 지원 우선 (아군 지원에 집중)
    5. 도망 우선 (안전한 위치로 후퇴)
    
    전략 결정 (형식: "전략: <전략명>, 이유: <이유>"):
    """
    
    # LLM 호출 로깅
    # print(f"LLM 호출 [전략 결정] - 캐릭터: {current_character.name}, 환경: {state.terrain}/{state.weather}")
    
    # LLM에 프롬프트 전송 (실제 구현 시 비동기 호출로 변경 필요)
    try:
        response = llm.invoke(prompt).content
        strategy_text = response.strip()
        # print(f"LLM 응답 [전략 결정] - {strategy_text[:100]}...")
    except Exception as e:
        print(f"LLM 호출 실패: {str(e)}")
        strategy_text = "전략: 공격 우선, 이유: 기본값 (LLM 오류)"
    
    # 전략 저장
    state.strategy = strategy_text
    
    # 트레이스 업데이트
    if state.trace:
        state.trace.append(f"전략 결정: {strategy_text}")
    
    print("[전략 결정 노드] 상태\n", state)
    
    return state

def plan_action(state: LangGraphBattleState) -> LangGraphBattleState:
    """
    행동 계획 수립 노드: 전략에 따른 구체적 행동 계획 수립 (LLM 호출)
    """
    print("[행동 계획 수립 노드] 시작")
    # 현재 캐릭터와 타겟 캐릭터 탐색
    current_character = next((c for c in state.characters if c.id == state.current_character_id), None)
    
    # 상대 진영 캐릭터 필터링
    opponent_type = "player" if current_character.type == "monster" else "monster"
    opponents = [c for c in state.characters if c.type == opponent_type]
    
    # 가장 가까운 상대 찾기
    if opponents:
        target_character = min(
            opponents, 
            key=lambda c: calculate_manhattan_distance(current_character.position, c.position)
        )
        target_id = target_character.id
    else:
        # 상대가 없으면 자기 자신을 타겟으로 (대기)
        target_id = current_character.id
    
    # PydanticOutputParser 설정
    parser = PydanticOutputParser(pydantic_object=ActionPlan)
    
    # 프롬프트 템플릿 설정
    prompt_template = PromptTemplate(
        template="""
        캐릭터: {character_name} ({character_type})
        위치: {position}
        자원: HP {hp}, AP {ap}, MOV {mov}
        사용 가능한 스킬: {skills}
        
        전략: {strategy}
        
        타겟 캐릭터 ID: {target_id}
        타겟 위치: {target_position}
        
        현재 위치에서 타겟을 향해 어떻게 움직이고, 어떤 스킬을 사용할지 결정하세요.
        이동은 한 턴에 최대 MOV값 만큼 가능합니다.
        
        {format_instructions}
        """,
        input_variables=["character_name", "character_type", "position", "hp", "ap", "mov", 
                        "skills", "strategy", "target_id", "target_position"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    # 프롬프트 구성
    prompt = prompt_template.format(
        character_name=current_character.name,
        character_type=current_character.type,
        position=current_character.position,
        hp=current_character.hp,
        ap=current_character.ap,
        mov=current_character.mov,
        skills=', '.join(current_character.skills),
        strategy=state.strategy,
        target_id=target_id,
        target_position=next((c.position for c in state.characters if c.id == target_id), None)
    )
    
    # # LLM 호출 로깅
    # print("[행동 계획 수립 노드] 프롬프트\n", prompt)
    
    try:
        # LLM 호출 및 파싱
        response = llm.invoke(prompt).content
        print("[행동 계획 수립 노드] 응답\n", response)
        
        # Pydantic 파서로 파싱
        action_plan = parser.parse(response)
        
    except Exception as e:
        print(f"LLM 호출 또는 파싱 실패: {str(e)}")
        # 폴백: 기본 행동
        action_plan = ActionPlan(
            move_to=current_character.position,
            skill=None,
            target_character_id=current_character.id,
            reason="기본 행동 (오류로 인한 폴백)",
            remaining_ap=current_character.ap,
            remaining_mov=current_character.mov
        )
    
    # 액션 플랜 저장
    state.action_plan = action_plan
    state.target_character_id = target_id
    
    # 트레이스 업데이트
    if state.trace:
        state.trace.append(f"행동 계획: {action_plan.skill} -> {action_plan.target_character_id}")
    
    print("[행동 계획 수립 노드] 상태\n", state)
    
    return state

def generate_dialogue(state: LangGraphBattleState) -> LangGraphBattleState:
    """
    대사 생성 노드: 캐릭터 행동에 맞는 대사 생성 (LLM 호출)
    """
    print("[대사 생성 노드] 시작")
    # 현재 캐릭터와 타겟 찾기
    current_character = next((c for c in state.characters if c.id == state.current_character_id), None)
    target_character = next((c for c in state.characters if c.id == state.target_character_id), None)
    
    # 대사 생성 프롬프트
    prompt = f"""
    당신은 '{current_character.name}'이라는 캐릭터입니다.
    캐릭터 특성: {', '.join(current_character.traits)}
    
    현재 상황:
    - {state.strategy}
    - 스킬 '{state.action_plan.skill}'을(를) 사용하여 '{target_character.name if target_character else "대상 없음"}'을(를) 공격/지원합니다.
    
    이 상황에서 판타지 RPG 세계관의 {current_character.name}의 말투로 간결한 대사를 한 문장으로 생성하세요:
    """
    
    # # LLM 호출 로깅
    # print(f"LLM 호출 [대사 생성] - 캐릭터: {current_character.name}, 스킬: {state.action_plan.skill}")
    
    # LLM에 프롬프트 전송
    try:
        response = llm.invoke(prompt).content
        dialogue = response.strip().strip('"\'')
        print(f"LLM 응답 [대사 생성] - '{dialogue}'")
    except Exception as e:
        print(f"LLM 호출 실패: {str(e)}")
        # 폴백: 기본 대사
        dialogue = f"{current_character.name}의 차례!"
    
    # 대사 저장
    state.dialogue = dialogue
    
    # 액션 플랜에도 대사 추가
    if state.action_plan:
        state.action_plan.dialogue = dialogue
    
    # 트레이스 업데이트
    if state.trace:
        state.trace.append(f"대사 생성: '{dialogue}'")
    
    print("[대사 생성 노드] 상태\n", state)
    
    return state

def create_response(state: LangGraphBattleState) -> LangGraphBattleState:
    """
    응답 생성 노드: 최종 상태를 API 응답 형태로 정리
    """
    # 최종 트레이스 업데이트
    if state.trace:
        state.trace.append("응답 생성 완료")
    
    # 여기서는 단순히 상태를 반환
    # 실제 API 응답 변환은 _convert_output_to_action 함수에서 수행
    return state
