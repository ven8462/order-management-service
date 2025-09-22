from sqlalchemy import Column, Integer, String, DateTime, func, Numeric, CheckConstraint, Index
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String(100), nullable=False, index=True)
    product_name = Column(String(100), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)  # safer for money
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Constraints
    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_quantity_positive"),
        CheckConstraint("total_amount >= 0", name="check_amount_nonnegative"),
        Index("idx_customer_product", "customer_name", "product_name"),
    )

    def __repr__(self):
        return (
            f"<Order(id={self.id}, customer_name='{self.customer_name}', "
            f"product_name='{self.product_name}', quantity={self.quantity}, "
            f"total_amount={self.total_amount}, status='{self.status}', "
            f"created_at={self.created_at})>"
        )
        
        
