from sqlalchemy.orm import Session
from . import models, schemas
import logging
import json
from .redis_client import get_redis_client

CACHE_TTL = 60 * 5  # 5 minutes

logger = logging.getLogger("uvicorn.error")

def invalidate_order_history_cache(order_id: int):
    """Remove cached history for an order when new history is added."""
    redis_client = get_redis_client()
    keys = redis_client.keys(f"order:{order_id}:history:*")
    if keys:
        redis_client.delete(*keys)
        logging.debug(f"Invalidated cache for order {order_id}")


# Implements CQRS by having separate functions for writes (commands) and reads (queries)

# --- COMMANDS (Write Operations) ---
def create_order(db: Session, order: schemas.OrderCreate) -> models.Order:
    db_order = None  # initialize variable
    try:
        total_amount = sum(item.quantity * item.price for item in order.items)
        db_order = models.Order(user_id=order.user_id, total_amount=total_amount)
        db.add(db_order)
        db.commit()  # Commit to get the order ID

        for item in order.items:
            db_item = models.OrderItem(**item.dict(), order_id=db_order.id)
            db.add(db_item)

        db.add(models.OrderStatusHistory(order_id=db_order.id, status=models.OrderStatusEnum.PENDING))
        db.commit()
        db.refresh(db_order)

        # Invalidate cache (new order created)
        try:
            invalidate_order_history_cache(db_order.id)
        except Exception as e:
            logging.error(f"Failed to invalidate cache for order {db_order.id}: {e}")

        logging.info(f"Created order {db_order.id} with status PENDING.")
        return db_order

    except Exception as e:
        logging.error(f"Failed to create order: {e}")
        if db_order:
            # Only update status if db_order exists
            crud.update_order_status(db, db_order.id, models.OrderStatusEnum.FAILED)
        raise  # re-raise the exception

def update_order_status(db: Session, order_id: int, status: models.OrderStatusEnum) -> models.Order:
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if db_order:
        db_order.status = status
        db.add(models.OrderStatusHistory(order_id=order_id, status=status))
        db.commit()
        db.refresh(db_order)

      # Invalidate cache (new order created)
        invalidate_order_history_cache(db_order.id)

        logging.info(f"Updated order {order_id} status to {status.value}")
    return db_order


# --- QUERIES (Read Operations) ---
def get_order(db: Session, order_id: int):
    return db.query(models.Order).filter(models.Order.id == order_id).first()

def get_orders_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Order).filter(models.Order.user_id == user_id).offset(skip).limit(limit).all()

def get_order_history(db: Session, order_id: int, skip: int = 0, limit: int = 50):
    logger.info(f"Fetching order history for order_id={order_id}, skip={skip}, limit={limit}")
    cache_key = f"order:{order_id}:history:{skip}:{limit}"

    # 1. Try cache
    redis_client = get_redis_client()
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # 2. Fallback to DB
    results = (
        db.query(models.OrderStatusHistory)
        .filter(models.OrderStatusHistory.order_id == order_id)
        .order_by(models.OrderStatusHistory.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    logger.info(f"DB query returned {len(results)} rows for order_id={order_id}")

    # 3. Serialize results for cache
    results_dict = [
        {
            "id": r.id,
            "order_id": r.order_id,
            "status": r.status,
            "created_at": r.created_at.isoformat(),
        }
        for r in results
    ]

    redis_client.setex(cache_key, CACHE_TTL, json.dumps(results_dict))

    return results_dict