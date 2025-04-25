from pydantic import BaseModel, Field
from uuid import UUID
from enum import Enum
from typing import Optional, Dict, Any, List

from app.models.items import EquipmentMaster

class JobType(str, Enum):
    warrior = "warrior"
    archer = "archer"

class GenderType(str, Enum):
    M = "M"
    F = "F"

class Position(BaseModel):
    x: float
    y: float
    z: float

    class Config:
        json_schema_extra = {
            "example": {
                "x": 0.0,
                "y": 0.0,
                "z": 0.0
            }
        }

class CharacterStats(BaseModel):
    hp: int
    attack: int
    defense: int
    resistance: int
    critical_rate: float
    critical_damage: float
    move_range: int
    speed: int
    points: int

class CharacterInfo(BaseModel):
    character_id: UUID
    character_name: str
    job: JobType
    gender: GenderType
    traits: List[str]
    level: int
    current_exp: int
    max_exp: int
    position: Position
    stats: CharacterStats

class CharacterInfoRequest(BaseModel):
    user_id: UUID

class CharacterCreateRequest(BaseModel):
    user_id: UUID
    character_name: str = Field(..., max_length=10)
    job: JobType
    gender: GenderType
    traits: List[str]

class CharacterUpdateRequest(BaseModel):
    character_id: UUID
    level: Optional[int] = None
    current_exp: Optional[int] = None
    max_exp: Optional[int] = None
    traits: Optional[List[str]] = None
    position: Optional[Position] = None

class CharacterStatsUpdateRequest(BaseModel):
    character_id: UUID
    hp: Optional[int] = None
    attack: Optional[int] = None
    defense: Optional[int] = None
    resistance: Optional[int] = None
    critical_rate: Optional[float] = None
    critical_damage: Optional[float] = None
    move_range: Optional[int] = None
    speed: Optional[int] = None
    points: Optional[int] = None

class CharacterUpdateResponse(BaseModel):
    message: str

class CharacterCreateResponse(BaseModel):
    message: str
    character_id: UUID

class CharacterStatsUpdateResponse(BaseModel):
    message: str

class CharacterInfoResponse(BaseModel):
    message: str
    user_id: UUID
    character_info: CharacterInfo
    equipment_info: List[EquipmentMaster]