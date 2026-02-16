from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel


class OrderCreate(BaseModel):
    items: List[Dict]
    total_price: float


class Order(BaseModel):
    id: str
    user_id: int
    items: List[Dict]
    total_price: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class OrderUpdate(BaseModel):
    status: str
