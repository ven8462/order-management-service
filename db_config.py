from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Format: postgresql+psycopg2://username:password@host:port/dbname
DATABASE_URL = "postgresql+psycopg2://order_user:WacekeMwangi@123@localhost:5432/order_management_db"

# 🚨 Wrong: order_user:WacekeMwangi@123@localhost
# 🚀 Correct: order_user:"WacekeMwangi@123"@localhost

# Since your password contains '@', wrap it in URL encoding:
# @ becomes %40
DATABASE_URL = "postgresql+psycopg2://order_user:WacekeMwangi%40123@localhost:5432/order_management_db"

engine = create_engine(DATABASE_URL, echo=True)

Base = declarative_base()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
