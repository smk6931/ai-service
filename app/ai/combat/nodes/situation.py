from typing import Dict, Any, List
from langchain_core.messages import SystemMessage

from app.ai.combat.states import CombatState
from app.models.combat import BattleStateForAI, CharacterForAI
from app.ai.combat.utils import find_targets_in_range, calculate_movable_positions, get_current_character
from app.ai.combat.nodes import debug_node


def analyze_situation(state: CombatState) -> Dict[str, Any]:
    """전투 상황을 분석하는 노드
    
    현재 캐릭터 상태, 공격 가능한 타겟, 이동 가능한 범위 등을 분석합니다.
    
    Args:
        state: 현재 전투 상태
        
    Returns:
        상황 분석 결과가 포함된 상태 업데이트
    """
    # 입력값 디버깅
    debug_node("analyze_situation", input_data=state)
    
    battle_state = state["battle_state"]
    current = get_current_character(battle_state)
    
    if not current:
        # 현재 캐릭터가 없는 경우 에러 반환
        result = {
            "situation_analysis": {"error": "현재 캐릭터를 찾을 수 없습니다"},
            "messages": [SystemMessage(content="[시스템] 현재 캐릭터 정보를 찾을 수 없습니다.")]
        }
        # 출력값 디버깅 (에러 상태)
        debug_node("analyze_situation", output_data=result, error=True)
        return result
    
    # 타겟과 이동 범위 분석
    targets_in_range = find_targets_in_range(battle_state)
    movable_positions = calculate_movable_positions(battle_state)
    target_characters = get_target_characters(battle_state, current)
    
    # 분석 결과 생성
    situation_analysis = {
        "current_character": create_character_summary(current),
        "targets_in_range": targets_in_range,
        # "movable_positions_count": len(movable_positions),
        # "movable_positions": limit_list(movable_positions, 10),  # 이동 가능한 위치가 많을 경우 일부만 표시
        "movable_positions": movable_positions,
        "target_characters_count": len(target_characters),
        "target_characters": [create_target_summary(c) for c in target_characters],
        "battle_environment": {
            "terrain": battle_state.terrain,
            "weather": battle_state.weather,
            "cycle": battle_state.cycle,
            "turn": battle_state.turn
        }
    }
    
    # 요약 메시지 생성
    summary_content = create_summary_message(
        current, targets_in_range, movable_positions, target_characters, battle_state
    )
    
    result = {
        "situation_analysis": situation_analysis,
        "messages": [SystemMessage(content=summary_content)]
    }
    
    # 출력값 디버깅
    debug_node("analyze_situation", output_data=result)
    
    return result


def get_target_characters(battle_state: BattleStateForAI, current: CharacterForAI) -> List[CharacterForAI]:
    """현재 캐릭터와 다른 타입의 캐릭터들을 반환합니다.
    
    Args:
        battle_state: 전투 상태
        current: 현재 캐릭터
        
    Returns:
        타겟 캐릭터 목록
    """
    # 현재 캐릭터가 몬스터면 플레이어를, 플레이어면 몬스터를 타겟으로 함
    target_type = "player" if current.type == "monster" else "monster"
    return [c for c in battle_state.characters if c.type == target_type]


def create_character_summary(character: CharacterForAI) -> Dict[str, Any]:
    """캐릭터 정보 요약을 생성합니다.
    
    Args:
        character: 캐릭터 객체
        
    Returns:
        캐릭터 정보 요약
    """
    return {
        "id": character.id,
        "name": character.name,
        "type": character.type,
        "position": character.position,
        "hp": character.hp,
        "ap": character.ap,
        "mov": character.mov,
        "status_effects": character.status_effects,
        "traits": character.traits,
        "skills": character.skills
    }


def create_target_summary(character: CharacterForAI) -> Dict[str, Any]:
    """타겟 캐릭터 요약을 생성합니다.
    
    Args:
        character: 타겟 캐릭터 객체
        
    Returns:
        타겟 정보 요약
    """
    return {
        "id": character.id,
        "name": character.name,
        "position": character.position,
        "hp": character.hp,
        "distance": character.distance
    }


def limit_list(items: List, max_length: int) -> List:
    """리스트의 길이를 제한합니다.
    
    Args:
        items: 원본 리스트
        max_length: 최대 길이
        
    Returns:
        제한된 리스트
    """
    return items[:max_length] if len(items) > max_length else items


def create_summary_message(
    current: CharacterForAI,
    targets_in_range: Dict[str, List[str]],
    movable_positions: List,
    target_characters: List[CharacterForAI],
    battle_state: BattleStateForAI
) -> str:
    """분석 결과의 요약 메시지를 생성합니다.
    
    Args:
        current: 현재 캐릭터
        targets_in_range: 사거리 내 타겟
        movable_positions: 이동 가능한 위치 목록
        target_characters: 타겟 캐릭터 목록
        battle_state: 전투 상태
        
    Returns:
        요약 메시지
    """
    return f"""[시스템] 전투 상황 분석 완료:
- 현재 캐릭터: {current.name} ({current.type})
- HP: {current.hp}, AP: {current.ap}, MOV: {current.mov}
- 위치: {current.position}
- 공격 가능한 타겟 수: {sum(len(targets) for targets in targets_in_range.values())}
- 이동 가능한 위치 수: {len(movable_positions)}
- 타겟 캐릭터 수: {len(target_characters)}
- 환경: {battle_state.terrain} / {battle_state.weather}
""" 