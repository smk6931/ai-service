from typing import Dict, List, Tuple, Any, Optional
from app.models.combat import BattleStateForAI, CharacterForAI
from app.utils.combat import calculate_manhattan_distance
from app.utils.loader import skills


def find_targets_in_range(state: BattleStateForAI) -> Dict[str, List[str]]:
    """현재 캐릭터의 각 스킬에 대해 사거리 내에 있는 대상 목록을 찾습니다"""
    current = next((c for c in state.characters if c.id == state.current_character_id), None)
    if not current or not current.skills:
        return {}
    
    # 현재 캐릭터의 위치와 타입
    current_position = current.position
    current_type = current.type
    
    # 스킬별 사거리 내 대상 목록
    targets_in_range = {}
    
    # 현재 캐릭터와 다른 타입의 캐릭터를 대상으로 함 (몬스터→플레이어, 플레이어→몬스터)
    target_type = "player" if current_type == "monster" else "monster"
    target_characters = [c for c in state.characters if c.type == target_type]
    
    # 각 스킬에 대해 사거리 확인
    for skill_name in current.skills:
        # 스킬 정보 가져오기
        skill_data = skills.get(skill_name, {})
        skill_range = skill_data.get('range', 1)
        
        targets_in_range[skill_name] = []
        
        # 각 타겟 캐릭터와의 거리 계산하여 사거리 내에 있는지 확인
        for character in target_characters:
            distance = calculate_manhattan_distance(current_position, character.position)
            if distance <= skill_range:
                targets_in_range[skill_name].append(character.id)
    
    return targets_in_range


def calculate_movable_positions(state: BattleStateForAI) -> List[Tuple[int, int]]:
    """현재 캐릭터의 MOV 값을 기준으로 이동 가능한 모든 위치를 계산합니다"""
    current = next((c for c in state.characters if c.id == state.current_character_id), None)
    if not current:
        return []
    
    # 현재 위치와 이동력
    x, y = current.position
    mov = current.mov
    
    # 이동 가능한 모든 위치 (맨해튼 거리 이내)
    movable_positions = []
    
    # 맨해튼 거리로 이동 가능한 범위 계산 (상하좌우 이동만 가능)
    for dx in range(-mov, mov + 1):
        remaining_mov = mov - abs(dx)
        for dy in range(-remaining_mov, remaining_mov + 1):
            if abs(dx) + abs(dy) <= mov:  # 맨해튼 거리 확인
                new_pos = (x + dx, y + dy)
                movable_positions.append(new_pos)
    
    return movable_positions


def get_current_character(state: BattleStateForAI) -> Optional[CharacterForAI]:
    """현재 행동할 캐릭터를 반환합니다"""
    return next((c for c in state.characters if c.id == state.current_character_id), None) 