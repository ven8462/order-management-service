import enum
from sqlalchemy import (
    Column, String, Float, Integer, DateTime, ForeignKey, Enum as SQLAlchemyEnum, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class OrderStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    PAYMENT_PROCESSING = "PAYMENT_PROCESSING"
    INVENTORY_RESERVING = "INVENTORY_RESERVING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    status = Column(SQLAlchemyEnum(OrderStatusEnum), nullable=False, default=OrderStatusEnum.PENDING)
    total_amount = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    status_history = relationship("OrderStatusHistory", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    order = relationship("Order", back_populates="items")

class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    status = Column(SQLAlchemyEnum(OrderStatusEnum), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    order = relationship("Order", back_populates="status_history")

    # Composite index for performance on (order_id, created_at)
    __table_args__ = (
        Index("idx_order_created", "order_id", "created_at"),
    )