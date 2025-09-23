from sqlalchemy.orm import Session
from . import models, schemas
import logging

# Implements CQRS by having separate functions for writes (commands) and reads (queries)

# --- COMMANDS (Write Operations) ---
def create_order(db: Session, order: schemas.OrderCreate) -> models.Order:
    total_amount = sum(item.quantity * item.price for item in order.items)
    db_order = models.Order(user_id=order.user_id, total_amount=total_amount)
    db.add(db_order)
    db.commit() # Commit to get the order ID

    for item in order.items:
        db_item = models.OrderItem(**item.dict(), order_id=db_order.id)
        db.add(db_item)
    
    db.add(models.OrderStatusHistory(order_id=db_order.id, status=models.OrderStatusEnum.PENDING))
    db.commit()
    db.refresh(db_order)
    logging.info(f"Created order {db_order.id} with status PENDING.")
    return db_order

def update_order_status(db: Session, order_id: int, status: models.OrderStatusEnum) -> models.Order:
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if db_order:
        db_order.status = status
        db.add(models.OrderStatusHistory(order_id=order_id, status=status))
        db.commit()
        db.refresh(db_order)
        logging.info(f"Updated order {order_id} status to {status.value}")
    return db_order

# --- QUERIES (Read Operations) ---
def get_order(db: Session, order_id: int):
    return db.query(models.Order).filter(models.Order.id == order_id).first()

def get_orders_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Order).filter(models.Order.user_id == user_id).offset(skip).limit(limit).all()