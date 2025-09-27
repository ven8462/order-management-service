from db_config import engine, Base


def init_db():
    # This will create all tables in the database
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully.")


if __name__ == "__main__":
    init_db()
