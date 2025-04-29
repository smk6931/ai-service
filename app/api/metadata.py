from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Tuple

from app.utils.loader import skills, traits, status_effects

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
