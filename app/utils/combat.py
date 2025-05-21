from typing import Tuple, Dict, Any, List, Set

def calculate_manhattan_distance(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> int:
    """두 위치 간의 맨하탄 거리(가로+세로 이동 거리)를 계산합니다"""
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

def calculate_action_costs(
    current_position: Tuple[int, int], 
    target_position: Tuple[int, int], 
    current_ap: int, 
    current_mov: int, 
    skill_ap_cost: int
) -> Dict[str, Any]:
    """행동에 필요한 비용을 계산하고 남은 리소스를 반환합니다
    
    Args:
        current_position: 현재 캐릭터의 위치
        target_position: 이동 목표 위치
        current_ap: 현재 캐릭터의 AP
        current_mov: 현재 캐릭터의 MOV
        skill_ap_cost: 사용할 스킬의 AP 소모량
        
    Returns:
        dictionary: 비용 계산 결과 {'move_cost': int, 'remaining_ap': int, 'remaining_mov': int, 'can_perform': bool}
    """
    # 이동 거리 계산
    move_distance = calculate_manhattan_distance(current_position, target_position)
    
    # 이동 비용은 이동 거리만큼 MOV를 소모
    move_cost = move_distance
    
    # 남은 이동력 계산
    remaining_mov = current_mov - move_cost
    
    # 남은 AP 계산 (스킬 사용 비용 차감)
    remaining_ap = current_ap - skill_ap_cost
    
    # 행동 가능 여부 판단 (조건 세분화)
    mov_ok = remaining_mov >= 0
    ap_ok = remaining_ap >= 0
    can_perform = mov_ok and ap_ok
    
    # 더 상세한 정보 반환
    return {
        'move_cost': move_cost,
        'remaining_ap': max(0, remaining_ap),  # 음수 방지
        'remaining_mov': max(0, remaining_mov),  # 음수 방지
        'can_perform': can_perform,
        'reason_if_fail': None if can_perform else (
            "AP 부족" if not ap_ok else 
            "MOV 부족" if not mov_ok else 
            "알 수 없는 이유"
        )
    }
    
def calculate_reachable_positions(position: Tuple[int, int], mov: int) -> Set[Tuple[int, int]]:
    """현재 위치에서 MOV를 고려했을 때 도달 가능한 모든 위치를 계산합니다
    
    Args:
        position: 현재 위치 (x, y)
        mov: 이동력
        
    Returns:
        Set[Tuple[int, int]]: 도달 가능한 위치 집합
    """
    reachable = {position}  # 현재 위치는 항상 포함
    
    # 모든 가능한 이동 거리 (1~mov)에 대해 계산
    for distance in range(1, mov + 1):
        for dx in range(-distance, distance + 1):
            dy_max = distance - abs(dx)
            for dy in range(-dy_max, dy_max + 1):
                if abs(dx) + abs(dy) <= distance:  # 맨하탄 거리 제한
                    new_pos = (position[0] + dx, position[1] + dy)
                    reachable.add(new_pos)
    
    return reachable

def filter_usable_skills(
    current_position: Tuple[int, int],
    target_position: Tuple[int, int],
    mov: int,
    skills: List[str],
    skill_info_map: Dict[str, Dict]
) -> Dict[str, List[str]]:
    """현재 위치와 MOV를 고려하여 사용 가능한 스킬을 필터링합니다
    
    Args:
        current_position: 현재 위치 (x, y)
        target_position: 타겟 위치 (x, y)
        mov: 이동력
        skills: 스킬 이름 목록
        skill_info_map: 스킬 정보 맵 (스킬 이름 -> 정보)
    
    Returns:
        Dict[str, List[str]]: 
            {
                'immediately_usable': 현재 위치에서 바로 사용 가능한 스킬 목록,
                'reachable_usable': 이동 후 사용 가능한 스킬 목록,
                'unusable': 사용 불가능한 스킬 목록
            }
    """
    immediately_usable = []
    reachable_usable = []
    unusable = []
    
    # 현재 타겟과의 거리
    current_distance = calculate_manhattan_distance(current_position, target_position)
    
    # 도달 가능한 위치 계산
    reachable_positions = calculate_reachable_positions(current_position, mov)
    
    # 이동 후 가능한 최소 거리 계산
    min_possible_distance = float('inf')
    for pos in reachable_positions:
        dist = calculate_manhattan_distance(pos, target_position)
        min_possible_distance = min(min_possible_distance, dist)
    
    # 각 스킬에 대해 사용 가능 여부 검사
    for skill_name in skills:
        skill_info = skill_info_map.get(skill_name, {})
        skill_range = skill_info.get('range', 1)  # 기본 사거리 1
        
        if current_distance <= skill_range:
            # 현재 위치에서 바로 사용 가능
            immediately_usable.append(skill_name)
        elif min_possible_distance <= skill_range:
            # 이동 후 사용 가능
            reachable_usable.append(skill_name)
        else:
            # 사용 불가능
            unusable.append(skill_name)
    
    return {
        'immediately_usable': immediately_usable,
        'reachable_usable': reachable_usable,
        'unusable': unusable
    } 