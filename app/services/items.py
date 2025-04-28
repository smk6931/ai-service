from datetime import datetime
from sqlalchemy.orm import Session

from app.db.database import mongo_client
from app.db.items import Item
from app.db.characters import Character

from app.models.items import (
    EquipmentUpsertRequest, 
    EquipmentGetRequest, 
    InventoryUpsertRequest, 
    InventoryGetRequest, 
    EquipmentMaster, 
    EquipmentItem,
    InventoryMaster,
    InventoryItem
)

def get_character_equipment(request: EquipmentGetRequest, db: Session) -> EquipmentMaster:
    character = db.query(Character).filter(Character.character_id == request.character_id).first()
    if not character:
        raise ValueError("캐릭터가 존재하지 않습니다.")
    
    equipment_doc = mongo_client["equipment"].find_one({"character_id": str(request.character_id)})
    if not equipment_doc:
        return EquipmentMaster(item_list=[])
    
    equipments = equipment_doc['equipment_info']
    
    item_list = []
    
    for equipment in equipments:
        item = db.query(Item).filter(Item.item_id == equipment['item_id']).first()
        if item:
            equipment_info = EquipmentItem(
                item_id=equipment['item_id'],
                item_category=item.item_category,
                item_type=item.item_type,
                item_class=item.item_class,
                item_name=item.item_name,
                category_name=item.category_name,
                description=item.description,
                level=item.level,
                price=item.price,
                options=equipment['options']
            )
            item_list.append(equipment_info)
    
    return EquipmentMaster(item_list=item_list)

def upsert_character_equipment(request: EquipmentUpsertRequest, db: Session):
    character = db.query(Character).filter(Character.character_id == request.character_id).first()
    if not character:
        raise ValueError("캐릭터가 존재하지 않습니다.")
    
    item_ids = [entry.item_id for entry in request.equipment_info]
    existing_items = db.query(Item).filter(Item.item_id.in_(item_ids)).all()
    existing_ids_set = set(item.item_id for item in existing_items)
    
    for item_id in item_ids:
        if item_id not in existing_ids_set:
            raise ValueError(f"{item_id} : 존재하지 않는 아이템입니다.")
    
    update_doc = {
        "$set": {
            "equipment_info": [
                {
                    "item_id": entry.item_id,
                    **({"options": entry.options.dict()} if entry.options else {})
                }
                for entry in request.equipment_info
            ]
        },
        "$currentDate": {
            "last_updated": True
        }
    }

    result = mongo_client["equipment"].update_one(
        {"character_id": str(request.character_id)},
        update_doc,
        upsert=True
    )

    return result

def get_character_inventory(request: InventoryGetRequest, db: Session) -> InventoryMaster:
    character = db.query(Character).filter(Character.character_id == request.character_id).first()
    if not character:
        raise ValueError("캐릭터가 존재하지 않습니다.")
    
    inventory_doc = mongo_client["inventory"].find_one({"character_id": str(request.character_id)})
    if not inventory_doc:
        return InventoryMaster(item_list=[], gold=0)
    
    inventory_info = inventory_doc['inventory_info']
    item_list = []
    
    for inventory in inventory_info:
        item = db.query(Item).filter(Item.item_id == inventory['item_id']).first()
        if item:
            inventory_item = InventoryItem(
                item_id=inventory['item_id'],
                counts=inventory['counts'],
                item_category=item.item_category,
                item_type=item.item_type if hasattr(item, 'item_type') else None,
                item_class=item.item_class,
                item_name=item.item_name,
                category_name=item.category_name,
                description=item.description,
                level=item.level,
                price=item.price if hasattr(item, 'price') else None,
                options=inventory['options'] if 'options' in inventory else None
            )
            item_list.append(inventory_item)
    
    gold = inventory_doc['gold']
    return InventoryMaster(item_list=item_list, gold=gold)

def upsert_character_inventory(request: InventoryUpsertRequest, db: Session):
    character = db.query(Character).filter(Character.character_id == request.character_id).first()
    if not character:
        raise ValueError("캐릭터가 존재하지 않습니다.")
    
    item_ids = [entry.item_id for entry in request.inventory_info]
    existing_items = db.query(Item).filter(Item.item_id.in_(item_ids)).all()
    existing_ids_set = set(item.item_id for item in existing_items)
    
    for item_id in item_ids:
        if item_id not in existing_ids_set:
            raise ValueError(f"{item_id} : 존재하지 않는 아이템입니다.")
    
    update_doc = {
        "$set": {
            "inventory_info": [
                {
                    "item_id": entry.item_id,
                    "counts": entry.counts,
                    **({"options": entry.options.dict()} if entry.options else {})
                }
                for entry in request.inventory_info
            ],
            "gold": request.gold
        },
        "$currentDate": {
            "last_updated": True
        }
    }

    result = mongo_client["inventory"].update_one(
        {"character_id": str(request.character_id)},
        update_doc,
        upsert=True
    )

    return result
