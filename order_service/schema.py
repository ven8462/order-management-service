from pydantic import BaseModel
from .models import OrderStatusEnum


# --- Item Schemas ---
class OrderItemBase(BaseModel):
    product_id: str
    quantity: int
    price: float


class OrderItemCreate(OrderItemBase):
    pass


class OrderItem(OrderItemBase):
    id: int

    class Config:
        from_attributes = True


# --- Order Schemas ---
class OrderCreate(BaseModel):
    items: list[OrderItemCreate]
    shipping_address: str


class Order(BaseModel):
    id: int
    status: OrderStatusEnum
    total_amount: float
    items: list[OrderItem] = []

    class Config:
        from_attributes = True


class OrderStatusUpdate(BaseModel):
    status: OrderStatusEnum


class OrderStatusHistory(BaseModel):
    status: OrderStatusEnum
    timestamp: object

    class Config:
        from_attributes = True


# --- Cart Schemas ---
class CartItem(OrderItemBase):
    id: int

    class Config:
        from_attributes = True


class CartItemCreate(OrderItemBase):
    user_id: int


class Cart(BaseModel):
    id: int
    user_id: int
    items: list[CartItem] = []
    total_amount: float

    class Config:
        from_attributes = True
