from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..cache import get_cache, set_cache
from ..database import get_db
from ..dependencies import get_current_user
from ..kafka import send_new_order
from ..limiter import limiter

router = APIRouter()


@router.post("/orders/", response_model=schemas.Order)
@limiter.limit("10/minute")
async def create_order(
    request: Request,
    order: schemas.OrderCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    db_order = crud.create_order(db=db, order=order, user_id=user_id)
    order_dict = schemas.Order.model_validate(db_order).model_dump()
    set_cache(f"order:{db_order.id}", order_dict, 300)
    await send_new_order(db_order.id)
    return db_order


@router.get("/orders/{order_id}/", response_model=schemas.Order)
@limiter.limit("10/minute")
async def read_order(
    request: Request,
    order_id: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    cached = get_cache(f"order:{order_id}")
    if cached:
        if cached["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        return cached

    db_order = crud.get_order(db, order_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    if db_order.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    order_dict = schemas.Order.model_validate(db_order).model_dump()
    set_cache(f"order:{order_id}", order_dict, 300)
    return db_order


@router.patch("/orders/{order_id}/", response_model=schemas.Order)
@limiter.limit("10/minute")
async def update_order_status(
    request: Request,
    order_id: str,
    update: schemas.OrderUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    db_order = crud.get_order(db, order_id)
    if not db_order or db_order.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    updated = crud.update_order_status(db, order_id, update.status)
    order_dict = schemas.Order.model_validate(updated).model_dump()
    set_cache(f"order:{order_id}", order_dict, 300)
    return updated


@router.get("/orders/user/{user_id}/", response_model=list[schemas.Order])
@limiter.limit("10/minute")
async def read_user_orders(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user),
):
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return crud.get_orders_by_user(db, user_id)
