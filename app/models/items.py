from pydantic import BaseModel
from typing import List
from uuid import UUID
from datetime import datetime

class EquipmentOption(BaseModel):
    hp: int
    attack: int
    defense: int
    resistance: int
    critical_rate: float
    critical_damage: float
    move_range: int
    speed: int

class EquipmentMaster(BaseModel):
    item_id: str
    item_category: int
    item_type: int
    item_class: int
    item_name: str
    category_name: str
    description: str
    level: int
    price: int
    options: EquipmentOption

class EquimentCollection(BaseModel):
    item_id: str
    options: EquipmentOption
    
class EquipmentGetRequest(BaseModel):
    character_id: UUID

class EquipmentUpsertRequest(BaseModel):
    character_id: UUID
    equipment_info: List[EquimentCollection]

class EquipmentUpsertResponse(BaseModel):
    message: str

