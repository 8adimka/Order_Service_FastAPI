import uuid
from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field

from .models import OrderStatus


class OrderCreate(BaseModel):
    items: List[Dict]
    total_price: float = Field(..., gt=0, description="Total price must be positive")


class Order(BaseModel):
    id: uuid.UUID
    user_id: int
    items: List[Dict]
    total_price: float
    status: OrderStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderUpdate(BaseModel):
    status: OrderStatus
