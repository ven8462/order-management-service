from kafka.producer import publish_event

def create_order(order_id: int, user_id: int, items: list):
    event = {
        "order_id": order_id,
        "user_id": user_id,
        "items": items,
        "status": "OrderCreated"
    }
    publish_event("order_events", event)
    print(f"[Order Service] Emitted: {event}")