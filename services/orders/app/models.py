from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String

from .database import Base


class Order(Base):
    __tablename__ = "orders"
    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    items = Column(JSON, nullable=False)
    total_price = Column(Float, nullable=False)
    status = Column(String, default="PENDING", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
