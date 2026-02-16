from uuid import uuid4

from sqlalchemy.orm import Session

from . import models, schemas


def create_order(db: Session, order: schemas.OrderCreate, user_id: int):
    db_order = models.Order(
        id=str(uuid4()),
        user_id=user_id,
        items=order.items,
        total_price=order.total_price,
        status="PENDING",
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order


def get_order(db: Session, order_id: str):
    return db.query(models.Order).filter(models.Order.id == order_id).first()


def update_order_status(db: Session, order_id: str, status: str):
    db_order = get_order(db, order_id)
    if db_order:
        db_order.status = status
        db.commit()
        db.refresh(db_order)
    return db_order


def get_orders_by_user(db: Session, user_id: int):
    return db.query(models.Order).filter(models.Order.user_id == user_id).all()
