from pydantic import BaseModel, Field
from uuid import UUID
from enum import Enum
from typing import Optional, Dict, Any

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

class CharacterCreateRequest(BaseModel):
    user_id: UUID
    character_name: str = Field(..., max_length=10)
    job: JobType
    gender: GenderType

class CharacterUpdateRequest(BaseModel):
    character_id: UUID
    level: int
    current_exp: int
    max_exp: int
    position: Position

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
