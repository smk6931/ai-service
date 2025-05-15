from typing import Dict, Any
from langchain_core.messages import SystemMessage

from app.ai.combat.states import CombatState
from app.ai.combat.utils import find_targets_in_range, calculate_movable_positions, get_current_character
from app.ai.combat.nodes import debug_node


def analyze_situation(state: CombatState) -> Dict[str, Any]:
    """
    전투 상황을 분석하는 노드
    - 현재 캐릭터 상태 파악
    - 공격 가능한 타겟 분석
    - 이동 가능한 범위 계산
    - 지형, 날씨 등 환경 요소 고려
    """
    # 디버깅: 입력 데이터 출력
    debug_node("상황 분석 (시작)", input_data=state)
    
    battle_state = state["battle_state"]
    current = get_current_character(battle_state)
    
    if not current:
        result = {
            "situation_analysis": {"error": "현재 캐릭터를 찾을 수 없습니다"},
            "messages": [SystemMessage(content="[시스템] 현재 캐릭터 정보를 찾을 수 없습니다.")]
        }
        debug_node("상황 분석 (에러)", output_data=result)
        return result
    
    # 직접 공격 가능한 타겟 분석
    targets_in_range = find_targets_in_range(battle_state)
    
    # 이동 가능한 위치 계산
    movable_positions = calculate_movable_positions(battle_state)
    
    # 타겟 캐릭터들 분류
    target_type = "player" if current.type == "monster" else "monster"
    target_characters = [c for c in battle_state.characters if c.type == target_type]
    
    # 전체 분석 결과 생성
    situation_analysis = {
        "current_character": {
            "id": current.id,
            "name": current.name,
            "type": current.type,
            "position": current.position,
            "hp": current.hp,
            "ap": current.ap,
            "mov": current.mov,
            "status_effects": current.status_effects,
            "traits": current.traits,
            "skills": current.skills
        },
        "targets_in_range": targets_in_range,
        "movable_positions_count": len(movable_positions),
        "movable_positions": movable_positions[:10] if len(movable_positions) > 10 else movable_positions,  # 이동 가능한 위치가 많을 경우 일부만 표시
        "target_characters_count": len(target_characters),
        "target_characters": [{
            "id": c.id,
            "name": c.name,
            "position": c.position,
            "hp": c.hp,
            "distance": c.distance
        } for c in target_characters],
        "battle_environment": {
            "terrain": battle_state.terrain,
            "weather": battle_state.weather,
            "cycle": battle_state.cycle,
            "turn": battle_state.turn
        }
    }
    
    # 요약 메시지 생성
    summary_content = f"""[시스템] 전투 상황 분석 완료:
- 현재 캐릭터: {current.name} ({current.type})
- HP: {current.hp}, AP: {current.ap}, MOV: {current.mov}
- 위치: {current.position}
- 공격 가능한 타겟 수: {sum(len(targets) for targets in targets_in_range.values())}
- 이동 가능한 위치 수: {len(movable_positions)}
- 타겟 캐릭터 수: {len(target_characters)}
- 환경: {battle_state.terrain} / {battle_state.weather}
"""
    
    result = {
        "situation_analysis": situation_analysis,
        "messages": [SystemMessage(content=summary_content)]
    }
    
    # 디버깅: 출력 데이터 출력
    debug_node("상황 분석 (완료)", output_data=result)
    
    return result 