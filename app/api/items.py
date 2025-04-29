from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.services import items

from app.models.items import EquipmentUpsertRequest, EquipmentUpsertResponse, InventoryUpsertRequest, InventoryUpsertResponse

# from app.db.database import SessionLocal
from app.utils.database import get_db

router = APIRouter(prefix="/items", tags=["items"])

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

@router.post("/upsert/equipment", response_model=EquipmentUpsertResponse, status_code=200)
def upsert_character_equipment(data: EquipmentUpsertRequest, db: Session = Depends(get_db)):
    try:
        result = items.upsert_character_equipment(data, db)
        if result.upserted_id or result.modified_count:
            return {
                "message": "장비 반영 완료"
            }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/upsert/inventory", response_model=InventoryUpsertResponse, status_code=200)
def upsert_character_inventory(data: InventoryUpsertRequest, db: Session = Depends(get_db)):
    try:
        result = items.upsert_character_inventory(data, db)
        if result.upserted_id or result.modified_count:
            return {
                "message": "인벤토리 반영 완료"
            }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
