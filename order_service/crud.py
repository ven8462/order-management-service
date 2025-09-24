from sqlalchemy.orm import Session
from . import models, schema

# --- Order Functions ---
def create_order(db: Session, order: schema.OrderCreate) -> models.Order:
    total_amount = sum(item.quantity * item.price for item in order.items)
    db_order = models.Order(user_id=order.user_id, total_amount=total_amount)
    db.add(db_order)
    db.commit()
    for item in order.items:
        db_item = models.OrderItem(**item.dict(), order_id=db_order.id)
        db.add(db_item)
    db.add(models.OrderStatusHistory(order_id=db_order.id, status=models.OrderStatusEnum.PENDING))
    db.commit()
    db.refresh(db_order)
    return db_order

def update_order_status(
    db: Session,
    order_id: int,
    status: schema.OrderStatusEnum
    ) -> models.Order:
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if db_order:
        db_order.status = status
        db.add(models.OrderStatusHistory(order_id=order_id, status=status))
        db.commit()
        db.refresh(db_order)
    return db_order

def get_order(db: Session, order_id: int):
    return db.query(models.Order).filter(models.Order.id == order_id).first()

def get_orders_by_user(db: Session, user_id: int):
    return db.query(models.Order).filter(models.Order.user_id == user_id).all()

def get_order_status_history(db: Session, order_id: int):
    return(
        db.query(models.OrderStatusHistory)
        .filter(models.OrderStatusHistory.order_id == order_id)
        .all()
        )

# --- Cart Functions ---
def get_or_create_cart_by_user_id(db: Session, user_id: int) -> models.Cart:
    db_cart = db.query(models.Cart).filter(models.Cart.user_id == user_id).first()
    if not db_cart:
        db_cart = models.Cart(user_id=user_id)
        db.add(db_cart)
        db.commit()
        db.refresh(db_cart)
    return db_cart

def add_item_to_cart(
    db: Session,
     user_id: int,
     item: schema.OrderItemBase
     ) -> models.Cart:
    db_cart = get_or_create_cart_by_user_id(db, user_id)
    db_item = models.CartItem(**item.dict(), cart_id=db_cart.id)
    db.add(db_item)
    db.commit()
    db.refresh(db_cart)
    db_cart.total_amount = sum(i.price * i.quantity for i in db_cart.items)
    return db_cart

def get_cart_with_total(db: Session, user_id: int):
    db_cart = db.query(models.Cart).filter(models.Cart.user_id == user_id).first()
    if db_cart:
        db_cart.total_amount = sum(i.price * i.quantity for i in db_cart.items)
    return db_cart
