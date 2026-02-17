import uuid
from typing import Union

from sqlalchemy.orm import Session

from . import models, schemas


def create_order(db: Session, order: schemas.OrderCreate, user_id: int):
    db_order = models.Order(
        user_id=user_id,
        items=order.items,
        total_price=order.total_price,
        status=models.OrderStatus.PENDING,
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order


def get_order(db: Session, order_id: Union[str, uuid.UUID]):
    # Преобразуем строку в UUID если необходимо
    if isinstance(order_id, str):
        try:
            order_id = uuid.UUID(order_id)
        except ValueError:
            return None
    return db.query(models.Order).filter(models.Order.id == order_id).first()


def update_order_status(
    db: Session, order_id: Union[str, uuid.UUID], status: models.OrderStatus
):
    db_order = get_order(db, order_id)
    if db_order:
        db_order.status = status
        db.commit()
        db.refresh(db_order)
    return db_order


def get_orders_by_user(db: Session, user_id: int):
    return db.query(models.Order).filter(models.Order.user_id == user_id).all()
