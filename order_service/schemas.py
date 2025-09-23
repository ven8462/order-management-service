from pydantic import BaseModel
from typing import List
from .models import OrderStatusEnum

# Schemas for Order Items
class OrderItemBase(BaseModel):
    product_id: str
    quantity: int
    price: float

class OrderItemCreate(OrderItemBase):
    pass

class OrderItem(OrderItemBase):
    id: int
    order_id: int
    
    class Config:
        orm_mode = True

# Schemas for Order
class OrderBase(BaseModel):
    user_id: int

class OrderCreate(OrderBase):
    items: List[OrderItemCreate]

class Order(OrderBase):
    id: int
    status: OrderStatusEnum
    total_amount: float
    items: List[OrderItem] = []
    
    class Config:
        orm_mode = True

# Schema for manual status updates (as per assignment)
class OrderStatusUpdate(BaseModel):
    status: OrderStatusEnum