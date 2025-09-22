from sqlalchemy import create_engine
from models import Base

engine = create_engine(
    'postgresql+psycopg2://postgres:Ord3rM%40n%40g3r%243rv1c3@localhost/order_management_db'
)

# Create all tables based on models.py
Base.metadata.create_all(engine)

print("✅ Orders table created successfully!")
