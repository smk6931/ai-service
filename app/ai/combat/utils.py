from typing import Dict, List, Tuple, Any, Optional
from app.models.combat import BattleStateForAI, CharacterForAI
from app.utils.combat import calculate_manhattan_distance
from app.utils.loader import skills


def get_current_character(state: BattleStateForAI) -> Optional[CharacterForAI]:
    """현재 행동할 캐릭터를 반환합니다.
    
    Args:
        state: 전투 상태 객체
        
    Returns:
        현재 캐릭터 객체 또는 None (찾지 못한 경우)
    """
    return next((c for c in state.characters if c.id == state.current_character_id), None)


def find_targets_in_range(state: BattleStateForAI) -> Dict[str, List[str]]:
    """현재 캐릭터의 각 스킬별 사거리 내에 있는 대상 ID 목록을 찾습니다.
    
    Args:
        state: 전투 상태 객체
        
    Returns:
        스킬명을 키로, 사거리 내 대상 ID 목록을 값으로 하는 딕셔너리
    """
    current = get_current_character(state)
    if not current or not current.skills:
        return {}
    
    # 현재 캐릭터의 타입과 반대되는 타입 찾기
    target_type = "player" if current.type == "monster" else "monster"
    
    # 타겟 캐릭터들 (현재 캐릭터와 다른 타입)
    target_characters = [c for c in state.characters if c.type == target_type]
    
    # 각 스킬별 사거리 내 대상 찾기
    targets_in_range: Dict[str, List[str]] = {}
    
    for skill_name in current.skills:
        skill_data = skills.get(skill_name, {})
        skill_range = skill_data.get('range', 1)
        
        # 사거리 내의 타겟들만 필터링
        targets_in_range[skill_name] = [
            character.id 
            for character in target_characters
            if calculate_manhattan_distance(current.position, character.position) <= skill_range
        ]
    
    return targets_in_range


def calculate_movable_positions(state: BattleStateForAI) -> List[Tuple[int, int]]:
    """현재 캐릭터의 이동력(MOV)을 기준으로 이동 가능한 모든 위치를 계산합니다.
    
    Args:
        state: 전투 상태 객체
        
    Returns:
        이동 가능한 좌표 목록 [(x1, y1), (x2, y2), ...]
    """
    current = get_current_character(state)
    if not current:
        return []
    
    origin = current.position
    mov = current.mov
    
    movable_positions: List[Tuple[int, int]] = []
    x, y = origin
    
    # 맨해튼 거리로 이동 가능한 모든 위치 계산
    for dx in range(-mov, mov + 1):
        remaining_mov = mov - abs(dx)
        for dy in range(-remaining_mov, remaining_mov + 1):
            if abs(dx) + abs(dy) <= mov:
                new_pos = (x + dx, y + dy)
                if new_pos[0] < 0 or new_pos[0] >= 25 or new_pos[1] < 0 or new_pos[1] >= 25:
                    continue
                movable_positions.append(new_pos)
    
    return movable_positions


def get_character_by_id(state: BattleStateForAI, character_id: str) -> Optional[CharacterForAI]:
    """ID로 캐릭터 객체를 찾습니다.
    
    Args:
        state: 전투 상태 객체
        character_id: 찾을 캐릭터 ID
        
    Returns:
        찾은 캐릭터 객체 또는 None (찾지 못한 경우)
    """
    return next((c for c in state.characters if c.id == character_id), None)


def get_characters_by_type(state: BattleStateForAI, character_type: str) -> List[CharacterForAI]:
    """특정 타입의 캐릭터 목록을 반환합니다.
    
    Args:
        state: 전투 상태 객체
        character_type: 찾을 캐릭터 타입 ("player" 또는 "monster")
        
    Returns:
        지정한 타입의 캐릭터 목록
    """
    return [c for c in state.characters if c.type == character_type] 