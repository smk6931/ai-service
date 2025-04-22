from pydantic import BaseModel, Field
from uuid import UUID
from enum import Enum

class JobType(str, Enum):
    warrior = "warrior"
    archer = "archer"

class GenderType(str, Enum):
    M = "M"
    F = "F"

class CharacterCreateRequest(BaseModel):
    user_id: UUID
    character_name: str = Field(..., max_length=10)
    job: JobType
    gender: GenderType


class CharacterCreateResponse(BaseModel):
    message: str
