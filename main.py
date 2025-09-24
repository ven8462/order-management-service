from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Order

engine = create_engine(
    "postgresql+psycopg2://postgres:Ord3rM%40n%40g3r%243rv1c3@localhost/order_management_db"
)
Session = sessionmaker(bind=engine)
session = Session()

# Insert a sample order
new_order = Order(
    customer_name="Grace Mwangi",
    product_name="T-shirt",
    quantity=2,
    total_amount=50.00,  # safer than Float
)
session.add(new_order)
session.commit()
print(f"✅ Order added with ID: {new_order.id}")

# Query orders
orders = session.query(Order).all()
for o in orders:
    print(o)
