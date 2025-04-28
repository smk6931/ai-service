from sqlalchemy import Column, String, SmallInteger, Integer, Text, TIMESTAMP, func

from app.db.database import Base

class Item(Base):
    __tablename__ = "items"

    item_id = Column(String(50), primary_key=True)
    item_category = Column(SmallInteger, nullable=False)
    item_type = Column(SmallInteger, nullable=True)
    item_class = Column(SmallInteger, nullable=False)
    item_name = Column(Text, nullable=False)
    category_name = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    level = Column(SmallInteger, nullable=False)
    price = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())