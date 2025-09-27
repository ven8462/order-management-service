from sqlalchemy import create_engine

# Connection string
engine = create_engine(
    "postgresql+psycopg2://postgres:Ord3rM%40n%40g3r%243rv1c3@localhost/order_management_db"
)

try:
    connection = engine.connect()
    print("✅ Connected to PostgreSQL successfully!")
except Exception as e:
    print("❌ Connection failed:", e)
finally:
    try:
        connection.close()
    except NameError:
        pass
