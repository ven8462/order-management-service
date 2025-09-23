from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.order_service import call_inventory_service, call_payment_service
from src.database import get_order_details, save_order_to_db

app = FastAPI()


class OrderData(BaseModel):
    user_id: str
    items: list
    address_id: str
    payment_method_id: str


@app.post("/orders", status_code=201)
def create_order(order: OrderData):
    try:
        # Step 1: Call Inventory Service to reserve stock
        call_inventory_service(order.items)

        # Step 2: Call Payment Service to process payment
        payment_response = call_payment_service(order.model_dump())

        # Step 3: Check for successful payment and save to DB
        if payment_response.get("status") != "approved":
            raise HTTPException(status_code=400, detail="Payment failed.") # Corrected line

        save_order_to_db(order.model_dump(), payment_response.get("transaction_id"))

        return {"orderId": "mock-order-123", "status": "CONFIRMED"}

    except Exception as e:
        if "Stock unavailable" in str(e):
            raise HTTPException(status_code=400, detail="Failed to reserve stock.") from e
        if "Payment service is down" in str(e):
            raise HTTPException(status_code=500, detail="Payment service is down") from e
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/orders/{order_id}")
def get_order(order_id: str):
    # Retrieve order details from the database
    order_details = get_order_details(order_id)
    if not order_details:
        raise HTTPException(status_code=404, detail="Order not found")
    return order_details
