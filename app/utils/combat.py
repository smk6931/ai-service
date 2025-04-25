from typing import Tuple

def calculate_manhattan_distance(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> int:
    """두 위치 간의 맨하탄 거리(가로+세로 이동 거리)를 계산합니다"""
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

def calculate_action_costs(
    current_position: Tuple[int, int], 
    target_position: Tuple[int, int], 
    current_ap: int, 
    current_mov: int, 
    skill_ap_cost: int
) -> dict:
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
    
    # 행동 가능 여부 판단
    can_perform = remaining_mov >= 0 and remaining_ap >= 0
    
    return {
        'move_cost': move_cost,
        'remaining_ap': remaining_ap,
        'remaining_mov': remaining_mov,
        'can_perform': can_perform
    } 