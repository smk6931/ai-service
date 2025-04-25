from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Tuple

from app.utils.loader import skills, traits, status_effects, prompt_combat_rules

router = APIRouter(prefix="/metadata", tags=["metadata"])

@router.get("/skills")
async def get_skills() -> Dict[str, Any]:
    """모든 스킬 데이터를 조회합니다."""
    return {"skills": skills}

@router.get("/skills/{skill_name}")
async def get_skill(skill_name: str) -> Dict[str, Any]:
    """특정 스킬의 상세 정보를 조회합니다."""
    if skill_name not in skills:
        raise HTTPException(status_code=404, detail=f"스킬 '{skill_name}'을(를) 찾을 수 없습니다.")
    return {"skill": skills[skill_name]}

@router.get("/traits")
async def get_traits() -> Dict[str, Any]:
    """모든 특성 데이터를 조회합니다."""
    return {"traits": traits}

@router.get("/traits/{trait_name}")
async def get_trait(trait_name: str) -> Dict[str, Any]:
    """특정 특성의 상세 정보를 조회합니다."""
    if trait_name not in traits:
        raise HTTPException(status_code=404, detail=f"특성 '{trait_name}'을(를) 찾을 수 없습니다.")
    return {"trait": traits[trait_name]}

@router.get("/status-effects")
async def get_status_effects() -> Dict[str, Any]:
    """모든 상태 효과 데이터를 조회합니다."""
    return {"status_effects": status_effects}

@router.get("/status-effects/{effect_name}")
async def get_status_effect(effect_name: str) -> Dict[str, Any]:
    """특정 상태 효과의 상세 정보를 조회합니다."""
    if effect_name not in status_effects:
        raise HTTPException(status_code=404, detail=f"상태 효과 '{effect_name}'을(를) 찾을 수 없습니다.")
    return {"status_effect": status_effects[effect_name]}

@router.get("/combat-rules")
async def get_combat_rules() -> Dict[str, Any]:
    """전투 규칙 정보를 조회합니다."""
    return {"combat_rules": prompt_combat_rules}

@router.get("/distance")
async def calculate_manhattan_distance(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> Dict[str, Any]:
    """두 위치 사이의 맨하탄 거리를 계산합니다."""
    distance = abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
    return {
        "pos1": pos1, 
        "pos2": pos2, 
        "manhattan_distance": distance
    }

@router.get("/skills-by-range")
async def get_skills_by_range(min_range: int = 0, max_range: int = 10) -> Dict[str, List[str]]:
    """지정된 사거리 범위 내의 스킬 목록을 조회합니다."""
    in_range_skills = []
    
    for skill_name, skill_data in skills.items():
        skill_range = skill_data.get('range', 0)
        if min_range <= skill_range <= max_range:
            in_range_skills.append(skill_name)
    
    return {
        "min_range": min_range,
        "max_range": max_range,
        "skills": in_range_skills
    }

@router.post("/valid-targets")
async def get_valid_targets(
    skill_name: str, 
    attacker_pos: Tuple[int, int], 
    targets: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """스킬의 사거리를 기준으로 유효한 타겟 목록을 반환합니다."""
    if skill_name not in skills:
        raise HTTPException(status_code=404, detail=f"스킬 '{skill_name}'을(를) 찾을 수 없습니다.")
    
    skill_data = skills[skill_name]
    skill_range = skill_data.get('range', 0)
    
    valid_targets = []
    invalid_targets = []
    
    for target in targets:
        if "id" not in target or "position" not in target:
            continue
            
        target_id = target["id"]
        target_pos = target["position"]
        
        distance = abs(attacker_pos[0] - target_pos[0]) + abs(attacker_pos[1] - target_pos[1])
        
        if distance <= skill_range:
            valid_targets.append({
                "id": target_id,
                "position": target_pos,
                "distance": distance
            })
        else:
            invalid_targets.append({
                "id": target_id,
                "position": target_pos,
                "distance": distance
            })
    
    return {
        "skill": skill_name,
        "range": skill_range,
        "attacker_position": attacker_pos,
        "valid_targets": valid_targets,
        "invalid_targets": invalid_targets
    }
