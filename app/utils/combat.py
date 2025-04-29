from typing import Tuple, Dict, Any

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