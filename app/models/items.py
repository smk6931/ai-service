from pydantic import BaseModel
from typing import List, Optional
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
    
class ItemMaster(BaseModel):
    item_id: str
    item_category: int
    item_type: Optional[int] = None
    item_class: int
    item_name: str
    category_name: str
    description: str
    level: int
    price: Optional[int] = None
    options: Optional[EquipmentOption] = None

class EquipmentItem(ItemMaster):
    pass

class InventoryItem(ItemMaster):
    counts: int

class EquipmentMaster(BaseModel):
    item_list: List[EquipmentItem]

class InventoryMaster(BaseModel):
    item_list: List[InventoryItem]
    gold: int

class EquimentCollection(BaseModel):
    item_id: str
    options: EquipmentOption

class InventoryColection(BaseModel):
    item_id: str
    counts: int
    options: Optional[EquipmentOption] = None

class EquipmentGetRequest(BaseModel):
    character_id: UUID
    
class InventoryGetRequest(BaseModel):
    character_id: UUID

class EquipmentUpsertRequest(BaseModel):
    character_id: UUID
    equipment_info: List[EquimentCollection]

class InventoryUpsertRequest(BaseModel):
    character_id: UUID
    inventory_info: List[InventoryColection]
    gold: int

class EquipmentUpsertResponse(BaseModel):
    message: str

class InventoryUpsertResponse(BaseModel):
    message: str


