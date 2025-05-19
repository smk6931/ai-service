from typing import Dict, List, Tuple, Optional
from langchain_openai import ChatOpenAI
from app.ai.combat.states import LangGraphBattleState, Character, ActionPlan
from app.utils.combat import calculate_manhattan_distance

# LLM 인스턴스 생성 - 실제 구현 시 적절한 모델과 API 키 설정 필요
llm = ChatOpenAI(temperature=0.7)

def analyze_situation(state: LangGraphBattleState) -> LangGraphBattleState:
    """
    상황 분석 노드: 현재 전투 상황을 분석하고 캐릭터 간 거리, 위험도 등 계산
    """
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
    
    return state

def decide_strategy(state: LangGraphBattleState) -> LangGraphBattleState:
    """
    전략 결정 노드: 캐릭터 특성과 상황을 기반으로 행동 전략 결정 (LLM 호출)
    """
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
    2. 방어 우선 (회피 및 생존 중심)
    3. 지원 우선 (아군 지원에 집중)
    4. 도망 우선 (안전한 위치로 후퇴)
    
    전략 결정 (형식: "전략: <전략명>, 이유: <이유>"):
    """
    
    # LLM에 프롬프트 전송 (실제 구현 시 비동기 호출로 변경 필요)
    # 예시 응답: "전략: 공격 우선, 이유: HP가 충분하고 적이 가까이 있어 공격이 효과적"
    try:
        response = llm.invoke(prompt).content
        strategy_text = response.strip()
    except Exception as e:
        print(f"LLM 호출 실패: {str(e)}")
        strategy_text = "전략: 공격 우선, 이유: 기본값 (LLM 오류)"
    
    # 전략 저장
    state.strategy = strategy_text
    
    # 트레이스 업데이트
    if state.trace:
        state.trace.append(f"전략 결정: {strategy_text}")
    
    return state

def plan_action(state: LangGraphBattleState) -> LangGraphBattleState:
    """
    행동 계획 수립 노드: 전략에 따른 구체적 행동 계획 수립 (LLM 호출)
    """
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
    
    # 행동 계획 프롬프트 구성
    prompt = f"""
    캐릭터: {current_character.name} ({current_character.type})
    위치: {current_character.position}
    자원: HP {current_character.hp}, AP {current_character.ap}, MOV {current_character.mov}
    사용 가능한 스킬: {', '.join(current_character.skills)}
    
    전략: {state.strategy}
    
    타겟 캐릭터 ID: {target_id}
    타겟 위치: {next((c.position for c in state.characters if c.id == target_id), None)}
    
    현재 위치에서 타겟을 향해 어떻게 움직이고, 어떤 스킬을 사용할지 결정하세요.
    이동은 한 턴에 최대 MOV값 만큼 가능합니다.
    
    행동 계획 (JSON 형식):
    {{
        "move_to": [x, y],
        "skill": "스킬명",
        "target_character_id": "타겟 ID",
        "reason": "행동 이유",
        "remaining_ap": 남은 AP,
        "remaining_mov": 남은 MOV
    }}
    """
    
    # LLM에 프롬프트 전송 (예시 - 실제로는 응답 파싱 필요)
    try:
        response = llm.invoke(prompt).content
        
        # 실제 구현에서는 응답을 파싱하여 ActionPlan 객체 생성
        # 여기서는 간단한 예시만 제공
        x, y = current_character.position
        
        # 타겟 방향으로 한 칸 이동 (예시)
        target_pos = next((c.position for c in state.characters if c.id == target_id), None)
        if target_pos and current_character.mov > 0:
            tx, ty = target_pos
            dx = 1 if tx > x else (-1 if tx < x else 0)
            dy = 1 if ty > y else (-1 if ty < y else 0)
            
            if dx != 0:
                x += dx
            elif dy != 0:
                y += dy
        
        # 기본 액션 플랜
        action_plan = ActionPlan(
            move_to=(x, y),
            skill=current_character.skills[0] if current_character.skills else "대기",
            target_character_id=target_id,
            reason="전략에 따른 행동",
            remaining_ap=current_character.ap - 1 if current_character.ap > 0 else 0,
            remaining_mov=current_character.mov - 1 if current_character.mov > 0 else 0
        )
    except Exception as e:
        print(f"LLM 호출 실패: {str(e)}")
        # 폴백: 기본 행동
        action_plan = ActionPlan(
            move_to=current_character.position,
            skill="대기",
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
    
    return state

def generate_dialogue(state: LangGraphBattleState) -> LangGraphBattleState:
    """
    대사 생성 노드: 캐릭터 행동에 맞는 대사 생성 (LLM 호출)
    """
    # 현재 캐릭터와 타겟 찾기
    current_character = next((c for c in state.characters if c.id == state.current_character_id), None)
    target_character = next((c for c in state.characters if c.id == state.target_character_id), None)
    
    # 대사 생성 프롬프트
    prompt = f"""
    당신은 '{current_character.name}'이라는 {current_character.type} 캐릭터입니다.
    캐릭터 특성: {', '.join(current_character.traits)}
    
    현재 상황:
    - {state.strategy}
    - 스킬 '{state.action_plan.skill}'을(를) 사용하여 '{target_character.name if target_character else "대상 없음"}'을(를) 공격/지원합니다.
    
    이 상황에서 캐릭터가 말할 수 있는 간결한 대사를 한 문장으로 생성하세요:
    """
    
    # LLM에 프롬프트 전송
    try:
        response = llm.invoke(prompt).content
        dialogue = response.strip().strip('"\'')
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
