from typing import Dict, List, Tuple, Optional
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain.prompts import FewShotPromptTemplate

from app.ai.combat.states import LangGraphBattleState, Character, ActionPlan, Strategy
from app.utils.combat import calculate_manhattan_distance, calculate_action_costs, filter_usable_skills
from app.utils.loader import skill_info_all
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
    
    # PydanticOutputParser 설정
    parser = PydanticOutputParser(pydantic_object=Strategy)
    
    # 프롬프트 템플릿 설정
    prompt_template = PromptTemplate(
        template="""당신은 '{character_name}'이라는 {character_type} 캐릭터입니다.
캐릭터 특성: {character_traits}
현재 HP: {hp}, AP: {ap}, MOV: {mov}
상태 이상: {status_effects}

전투 환경:
- 지형: {terrain}
- 날씨: {weather}

전투 상황:
{battle_summary}

다음 중 하나의 전략을 선택하고 그 이유를 간략히 설명하세요:
1. 공격 우선 (근접한 적에게 최대 피해)
2. 처치 우선 (가장 약한 적에게 최대 피해)
3. 방어 우선 (회피 및 생존 중심)
4. 지원 우선 (아군 지원에 집중)
5. 도망 우선 (안전한 위치로 후퇴)

{format_instructions}""",
        input_variables=["character_name", "character_type", "character_traits", "hp", "ap", "mov", 
                        "status_effects", "terrain", "weather", "battle_summary"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    # 프롬프트 구성
    prompt = prompt_template.format(
        character_name=current_character.name,
        character_type=current_character.type,
        character_traits=', '.join(current_character.traits),
        hp=current_character.hp,
        ap=current_character.ap,
        mov=current_character.mov,
        status_effects=', '.join(current_character.status_effects) if current_character.status_effects else '없음',
        terrain=state.terrain,
        weather=state.weather,
        battle_summary=state.battle_summary
    )
    
    # # LLM 호출 로깅
    # print(f"[전략 결정 노드] 프롬프트\n{prompt}")
    
    # LLM에 프롬프트 전송
    try:
        response = llm.invoke(prompt).content
        print(f"[전략 결정 노드] 응답\n{response}")
        
        # Pydantic 파서로 파싱
        strategy_info = parser.parse(response)
        
        # 구조화된 전략 정보 저장
        state.strategy_info = strategy_info
        # 기존 문자열 형태의 전략도 저장 (호환성 유지)
        state.strategy = f"{strategy_info.type}, {strategy_info.reason}"
        
    except Exception as e:
        print(f"LLM 호출 또는 파싱 실패: {str(e)}")
        # 폴백: 기본 전략
        state.strategy = "공격 우선 (LLM 오류)"
        state.strategy_info = Strategy(type="공격 우선", reason="LLM 오류로 인한 기본 전략")
    
    # 트레이스 업데이트
    if state.trace:
        state.trace.append(f"전략 결정: {state.strategy}")
    
    # print("[전략 결정 노드] 상태\n", state)
    
    return state

def plan_attack(state: LangGraphBattleState) -> LangGraphBattleState:
    """
    공격 계획 수립 노드: 공격 위주의 행동 계획 수립 (LLM 호출)
    """
    print("[공격 계획 수립 노드] 시작")
    
    # 캐릭터 및 타겟 정보 가져오기
    current_character, targets_info = get_current_and_target_characters(state)
    current_position = current_character.position
    
    # 전략에 따라 타겟 선택
    selected_target = None
    if state.strategy_info:
        if state.strategy_info.type == "처치 우선":
            # 가장 약한 적 타겟으로 선택
            selected_target = targets_info["weakest_target"]
        else:
            # 기본: 가장 가까운 적 타겟으로 선택
            selected_target = targets_info["nearest_target"]
    else:
        # 기본: 가장 가까운 적 타겟으로 선택
        selected_target = targets_info["nearest_target"]
    
    target_id = selected_target["id"]
    target_position = selected_target["position"]
    
    # 타겟 정보 문자열 구성
    target_info = f"주요 타겟: {selected_target['name']} (ID: {selected_target['id']}, 위치: {selected_target['position']}, HP: {selected_target['hp']})"
    
    # 추가 타겟 정보 구성
    additional_targets_info = ""
    if targets_info["total_targets"] > 1:
        for target_type, target in targets_info.items():
            if target_type not in ["total_targets", "nearest_target", "weakest_target"] or \
               (target_type in ["nearest_target", "weakest_target"] and target["id"] != target_id):
                additional_targets_info += f"\n추가 타겟: {target['name']} (ID: {target['id']}, 위치: {target['position']}, HP: {target['hp']})"
    
    # 모든 타겟 정보 결합
    all_targets_info = f"{target_info}{additional_targets_info}"
    
    # 스킬 설명 준비
    skill_descriptions = prepare_skill_descriptions(current_character, current_position, target_position)
    
    # 현재 위치에서 타겟까지의 거리
    current_distance = calculate_manhattan_distance(current_position, target_position)
    
    # 공격용 프롬프트 접미사
    attack_prompt_suffix = f"""현재 위치에서 주요 타겟을 향해 어떻게 움직이고, 어떤 공격 스킬을 사용할지 결정하세요.
이동은 한 턴에 최대 MOV값 만큼 가능합니다.
스킬 사용 시 스킬 범위 내에 타겟이 있어야 합니다.
공격적인 접근과 최대 데미지를 주는 방법을 선택하세요.

타겟 정보:
{all_targets_info}"""
    
    # 프롬프트 생성
    prompt = create_action_plan_prompt(
        character_name=current_character.name,
        character_type=current_character.type,
        position=current_position,
        hp=current_character.hp,
        ap=current_character.ap,
        mov=current_character.mov,
        strategy=state.strategy,
        target_id=target_id,
        target_position=target_position,
        current_distance=current_distance,
        skill_descriptions=skill_descriptions,
        prompt_suffix=attack_prompt_suffix
    )
    
    # # LLM 호출 로깅
    # print("[공격 계획 수립 노드] 프롬프트\n", prompt)
    
    # LLM 호출 및 응답 처리
    action_plan = handle_llm_response(prompt, current_character, current_position)
    
    # 상태 업데이트
    state = update_state_with_action_plan(state, action_plan, target_id)
    
    # print("[공격 계획 수립 노드] 상태\n", state)
    
    return state

def plan_flee(state: LangGraphBattleState) -> LangGraphBattleState:
    """
    도주 계획 수립 노드: 도망 위주의 행동 계획 수립 (LLM 호출)
    """
    print("[도주 계획 수립 노드] 시작")
    
    # 캐릭터 및 타겟 정보 가져오기
    current_character, targets_info = get_current_and_target_characters(state)
    current_position = current_character.position
    
    # 도주 시에는 가장 가까운 적으로부터 도망치는 것을 우선시
    nearest_target = targets_info["nearest_target"]
    target_id = nearest_target["id"]
    target_position = nearest_target["position"]
    
    # 타겟 정보 문자열 구성
    target_info = f"주요 위협: {nearest_target['name']} (ID: {nearest_target['id']}, 위치: {nearest_target['position']}, HP: {nearest_target['hp']})"
    
    # 추가 타겟 정보 구성
    additional_threats_info = ""
    if targets_info["total_targets"] > 1:
        for target_type, target in targets_info.items():
            if target_type not in ["total_targets", "nearest_target", "weakest_target"] or \
               (target_type in ["nearest_target", "weakest_target"] and target["id"] != target_id):
                additional_threats_info += f"\n추가 위협: {target['name']} (ID: {target['id']}, 위치: {target['position']}, HP: {target['hp']})"
    
    # 모든 위협 정보 결합
    all_threats_info = f"{target_info}{additional_threats_info}"
    
    # 스킬 설명 준비
    skill_descriptions = prepare_skill_descriptions(current_character, current_position, target_position)
    
    # 현재 위치에서 타겟까지의 거리
    current_distance = calculate_manhattan_distance(current_position, target_position)
    
    # 도주용 프롬프트 접미사
    flee_prompt_suffix = f"""현재 위치에서 주요 위협과 추가 위협으로부터 멀어지고, 안전하게 대피할 방법을 결정하세요.
이동은 한 턴에 최대 MOV값 만큼 가능합니다.
방어 또는 회피 스킬을 사용하거나, 안전한 위치로 후퇴하는 것을 우선시하세요.
타겟과의 거리를 최대한 늘리고 생존에 집중하세요.

위협 정보:
{all_threats_info}"""
    
    # 프롬프트 생성
    prompt = create_action_plan_prompt(
        character_name=current_character.name,
        character_type=current_character.type,
        position=current_position,
        hp=current_character.hp,
        ap=current_character.ap,
        mov=current_character.mov,
        strategy=state.strategy,
        target_id=target_id,
        target_position=target_position,
        current_distance=current_distance,
        skill_descriptions=skill_descriptions,
        prompt_suffix=flee_prompt_suffix
    )
    
    # # LLM 호출 로깅
    # print("[도주 계획 수립 노드] 프롬프트\n", prompt)
    
    # LLM 호출 및 응답 처리
    action_plan = handle_llm_response(prompt, current_character, current_position)
    
    # 상태 업데이트
    state = update_state_with_action_plan(state, action_plan, target_id)
    
    # print("[도주 계획 수립 노드] 상태\n", state)
    
    return state

def generate_dialogue(state: LangGraphBattleState) -> LangGraphBattleState:
    """
    대사 생성 노드: 캐릭터 행동에 맞는 대사 생성 (LLM 호출)
    """
    print("[대사 생성 노드] 시작")
    # 현재 캐릭터와 타겟 찾기
    current_character = next((c for c in state.characters if c.id == state.current_character_id), None)
    target_character = next((c for c in state.characters if c.id == state.target_character_id), None)
    
    # few-shot 예제 설정
    few_shot_examples = [
        {
            'name': '골렘',
            'traits': '냉정함, 강인함',
            'strategy': '전투 태세를 유지하며 침착하게 대응하는 것이 적합하며, 냉정하고 신중한 성격으로 인해 무리하지 않고 질서를 유지하려는 판단을 내립니다.',
            'skill': '타격',
            'dialogue': '위반 감지. 대응 절차 개시.'
        },
        {
            'name': '앤트',
            'traits': '신중함',
            'strategy': '신중한 성격으로 인해 자연의 힘을 활용하여 전장의 균형을 맞추려는 판단을 내립니다.',
            'skill': '대지 가르기',
            'dialogue': '땅이.. 너희를 기억하지 않기를 바란다..'
        },
        {
            'name': '리자드맨',
            'traits': '충동적, 잔인함',
            'strategy': '적에게 망설임 없이 공격을 감행하는 것이 효과적이며, 충동적인 성격 때문에 즉각적이고 강력한 공격으로 적을 빠르게 제압하는 것이 적합하다고 판단됩니다.',
            'skill': '날카로운 발톱',
            'dialogue': '사람 피.. 더! 씹어..! 찢어..!'
        }
    ]
    
    # 예제 프롬프트 템플릿 설정
    example_prompt = PromptTemplate(
        input_variables=["name", "traits", "strategy", "skill", "dialogue"],
        template="""캐릭터: {name}
특성: {traits}
전략: {strategy}
스킬: {skill}
대사: {dialogue}"""
    )
    
    # FewShotPromptTemplate 설정
    few_shot_prompt = FewShotPromptTemplate(
        examples=few_shot_examples,
        example_prompt=example_prompt,
        prefix="""당신은 판타지 게임 세계관의 캐릭터 대사를 생성하는 AI입니다.
주어진 캐릭터 정보와 상황에 적합한 한 줄의 대사를 생성해 주세요.

###지시사항:
1. 캐릭터의 특성과 종족에 따른 독특한 말투 사용
2. 짧지만 강렬하고 기억에 남는 대사 작성
3. 현재 HP와 전투 상황에 맞는 감정 표현
4. 사용하는 스킬의 특성이 대사에 반영되도록 함
5. 판타지 세계관에 맞는 고어체나 특수한 표현 사용

###각 몬스터 유형별 말투 특징:
- 골렘: 기계적, 단조로운 어조, 짧은 문장, 1인칭 사용 희박
- 앤트: 느리고 묵직한 말투, 자연과 생명 언급 잦음, 의인화된 자연체 느낌, 호흡 길고 문장 완성도 높음
- 리자드맨: 짧고 끊어지는 말투, 'ㅅ', 'ㅆ' 발음 강조, 육식동물 같은 표현
- 고블린: 거친 말투, 비문법적 표현, 3인칭으로 자신 지칭""",
        suffix="""
아래 정보를 바탕으로 판타지 RPG 세계관의 {character_name}의 성격을 최대한 반영하여 상황에 어울리는 짧은 대사를 한 문장으로 작성하세요:
캐릭터: {character_name}
특성: {character_traits}
전략: {strategy}
스킬: {skill_name}
대사:
""",
        input_variables=["character_name", "character_traits", "strategy", "skill_name", "target_name"]
    )
    
    # 최종 프롬프트 구성
    prompt = few_shot_prompt.format(
        character_name=current_character.name,
        character_traits=', '.join(current_character.traits),
        strategy=state.strategy,
        skill_name=state.action_plan.skill if state.action_plan and state.action_plan.skill else "대기",
        target_name=target_character.name if target_character else "없음"
    )
        
    # LLM 호출 로깅
    # print("[대사 생성 노드] 프롬프트\n", prompt)
    print(f"LLM 호출 [대사 생성] - 캐릭터: {current_character.name}, 스킬: {state.action_plan.skill if state.action_plan else '없음'}")
    
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
    
    # print("[대사 생성 노드] 상태\n", state)
    
    return state

def create_response(state: LangGraphBattleState) -> LangGraphBattleState:
    """
    응답 생성 노드: 최종 상태를 API 응답 형태로 정리
    """
    # 최종 트레이스 업데이트
    if state.trace:
        state.trace.append("응답 생성 완료")
        print(f"[응답 생성 노드] 상태\n{state}")
    
    # 여기서는 단순히 상태를 반환
    # 실제 API 응답 변환은 _convert_output_to_action 함수에서 수행
    return state



# 공통 기능 모듈화
def get_current_and_target_characters(state: LangGraphBattleState) -> Tuple[Character, Dict[str, Dict]]:
    """
    현재 캐릭터와 타겟 캐릭터들을 찾는 공통 함수
    두 명의 대상(가장 가까운 적, 가장 약한 적)을 탐색
    
    반환:
        - current_character: 현재 캐릭터
        - targets_info: 타겟 정보 사전 {
            "total_targets": 타겟 수,
            "nearest_target": {"character": 캐릭터, "id": ID, "position": 위치, "name": 이름, "hp": HP},
            "weakest_target": {"character": 캐릭터, "id": ID, "position": 위치, "name": 이름, "hp": HP}
          }
    """
    current_character = next((c for c in state.characters if c.id == state.current_character_id), None)
    
    # 상대 진영 캐릭터 필터링
    opponent_type = "player" if current_character.type == "monster" else "monster"
    opponents = [c for c in state.characters if c.type == opponent_type]
    
    # 타겟 정보 초기화
    targets_info = {
        "total_targets": len(opponents)
    }
    
    if opponents:
        # 가장 가까운 상대 찾기
        nearest_target = min(
            opponents, 
            key=lambda c: calculate_manhattan_distance(current_character.position, c.position)
        )
        
        # 가장 약한 상대 찾기 (HP가 가장 낮은 상대)
        weakest_target = min(
            opponents,
            key=lambda c: c.hp
        )
        
        # 타겟 정보 저장
        targets_info["nearest_target"] = {
            "character": nearest_target,
            "id": nearest_target.id,
            "position": nearest_target.position,
            "name": nearest_target.name,
            "hp": nearest_target.hp
        }
        
        targets_info["weakest_target"] = {
            "character": weakest_target,
            "id": weakest_target.id,
            "position": weakest_target.position,
            "name": weakest_target.name,
            "hp": weakest_target.hp
        }
    else:
        # 상대가 없으면 자기 자신을 타겟으로 (대기)
        targets_info["total_targets"] = 0
        targets_info["nearest_target"] = {
            "character": current_character,
            "id": current_character.id,
            "position": current_character.position,
            "name": current_character.name,
            "hp": current_character.hp
        }
        
        targets_info["weakest_target"] = targets_info["nearest_target"]
    
    return current_character, targets_info

def prepare_skill_descriptions(current_character: Character, current_position: Tuple[int, int], 
                              target_position: Tuple[int, int]) -> List[str]:
    """
    사용 가능한 스킬 설명 준비
    """
    # 사용 가능한 스킬 필터링
    usable_skills = filter_usable_skills(
        current_position=current_position,
        target_position=target_position,
        mov=current_character.mov,
        skills=current_character.skills,
        skill_info_map=skill_info_all
    )
    
    # 스킬 설명 구성
    skill_descriptions = []
    
    # 즉시 사용 가능한 스킬 먼저 추가
    for skill in usable_skills['immediately_usable']:
        skill_info = skill_info_all.get(skill, {})
        description = skill_info.get('description', '설명 없음')
        ap_cost = skill_info.get('ap', 1)
        skill_range = skill_info.get('range', 1)
        skill_descriptions.append(f"- {skill} (AP: {ap_cost}, 범위: {skill_range}, 즉시 사용 가능): {description}")
    
    # 이동 후 사용 가능한 스킬 추가
    for skill in usable_skills['reachable_usable']:
        skill_info = skill_info_all.get(skill, {})
        description = skill_info.get('description', '설명 없음')
        ap_cost = skill_info.get('ap', 1)
        skill_range = skill_info.get('range', 1)
        skill_descriptions.append(f"- {skill} (AP: {ap_cost}, 범위: {skill_range}, 이동 후 사용 가능): {description}")
    
    return skill_descriptions

def create_action_plan_prompt(character_name: str, character_type: str, position: Tuple[int, int],
                             hp: int, ap: int, mov: int, strategy: str, target_id: str,
                             target_position: Tuple[int, int], current_distance: int,
                             skill_descriptions: List[str], prompt_suffix: str = "") -> str:
    """
    행동 계획 프롬프트 생성
    """
    # PydanticOutputParser 설정
    parser = PydanticOutputParser(pydantic_object=ActionPlan)
    
    # 프롬프트 템플릿 설정
    prompt_template = PromptTemplate(
        template="""캐릭터: {character_name} ({character_type})
위치: {position}
자원: HP {hp}, AP {ap}, MOV {mov}

전략: {strategy}

현재 타겟 ID: {target_id}
현재 타겟까지의 거리: {current_distance}

사용 가능한 스킬 정보:
{skill_descriptions}

{prompt_suffix}

{format_instructions}""",
        input_variables=["character_name", "character_type", "position", "hp", "ap", "mov", 
                        "strategy", "target_id", "current_distance",
                        "skill_descriptions", "prompt_suffix"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    # 프롬프트 구성
    prompt = prompt_template.format(
        character_name=character_name,
        character_type=character_type,
        position=position,
        hp=hp,
        ap=ap,
        mov=mov,
        strategy=strategy,
        target_id=target_id,
        current_distance=current_distance,
        skill_descriptions="\n".join(skill_descriptions) if skill_descriptions else "사용 가능한 스킬이 없습니다.",
        prompt_suffix=prompt_suffix
    )
    
    return prompt

def validate_action_plan(action_plan: ActionPlan, current_character: Character, 
                       current_position: Tuple[int, int]) -> ActionPlan:
    """
    행동 유효성 검증 및 자원 감소 계산
    """
    if action_plan.skill:
        skill_info = skill_info_all.get(action_plan.skill, {})
        skill_ap_cost = skill_info.get('ap', 1)
        
        # 이동 및 스킬 사용 비용 계산
        action_costs = calculate_action_costs(
            current_position=current_position,
            target_position=action_plan.move_to if action_plan.move_to else current_position,
            current_ap=current_character.ap,
            current_mov=current_character.mov,
            skill_ap_cost=skill_ap_cost
        )
        
        # 행동 가능 여부 확인
        if not action_costs['can_perform']:
            print(f"행동 불가: {action_costs['reason_if_fail']}")
            # 행동이 불가능할 경우 대기 행동으로 변경
            action_plan = ActionPlan(
                move_to=current_position,
                skill=None,
                target_character_id=current_character.id,
                reason=f"자원 부족으로 인한 대기 ({action_costs['reason_if_fail']})",
                remaining_ap=current_character.ap,
                remaining_mov=current_character.mov
            )
        else:
            # 행동 가능할 경우 남은 자원 업데이트
            action_plan.remaining_ap = action_costs['remaining_ap']
            action_plan.remaining_mov = action_costs['remaining_mov']
    else:
        # 스킬을 사용하지 않는 경우 (대기)
        if action_plan.move_to:
            # 이동만 하는 경우
            move_distance = calculate_manhattan_distance(current_position, action_plan.move_to)
            remaining_mov = current_character.mov - move_distance
            
            # 이동 가능 여부 확인
            if remaining_mov < 0:
                print(f"이동 불가: MOV 부족")
                action_plan.move_to = current_position
                action_plan.remaining_mov = current_character.mov
            else:
                action_plan.remaining_mov = remaining_mov
            
            action_plan.remaining_ap = current_character.ap
        else:
            # 아무것도 하지 않는 경우
            action_plan.move_to = current_position
            action_plan.remaining_ap = current_character.ap
            action_plan.remaining_mov = current_character.mov
    
    return action_plan

def handle_llm_response(prompt: str, current_character: Character, current_position: Tuple[int, int]) -> ActionPlan:
    """
    LLM 호출 및 응답 처리
    """
    try:
        # LLM 호출 및 파싱
        response = llm.invoke(prompt).content
        print(f"LLM 응답: {response[:100]}...")
        
        # Pydantic 파서로 파싱
        parser = PydanticOutputParser(pydantic_object=ActionPlan)
        action_plan = parser.parse(response)
        
        # 행동 유효성 검증 및 자원 감소 계산
        validated_action_plan = validate_action_plan(action_plan, current_character, current_position)
        
        return validated_action_plan
    except Exception as e:
        print(f"LLM 호출 또는 파싱 실패: {str(e)}")
        # 폴백: 기본 행동
        return ActionPlan(
            move_to=current_position,
            skill=None,
            target_character_id=current_character.id,
            reason="기본 행동 (오류로 인한 폴백)",
            remaining_ap=current_character.ap,
            remaining_mov=current_character.mov
        )

def update_state_with_action_plan(state: LangGraphBattleState, action_plan: ActionPlan, 
                                target_id: str) -> LangGraphBattleState:
    """
    액션 플랜으로 상태 업데이트
    """
    # 액션 플랜 저장
    state.action_plan = action_plan
    state.target_character_id = target_id
    
    # 트레이스 업데이트
    if state.trace:
        state.trace.append(f"행동 계획: {action_plan.skill} -> {action_plan.target_character_id}")
    
    return state