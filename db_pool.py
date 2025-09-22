# db_pool.py
import psycopg2
import os

# Database credentials from environment variables
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "your_password")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "order_db")

# Create a connection pool with a minimum and maximum number of connections
db_pool = psycopg2.pool.SimpleConnectionPool(
    1,
    20,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    dbname=DB_NAME,
)


def get_db_connection():
    """Fetches a connection from the pool."""
    try:
        conn = db_pool.getconn()
        return conn
    except Exception as e:
        print(f"Error getting connection from pool: {e}")
        return None


def return_db_connection(conn):
    """Returns a connection back to the pool."""
    if conn:
        db_pool.putconn(conn)


if __name__ == "__main__":
    print("Getting a connection from the pool...")
    conn = get_db_connection()
    if conn:
        print("Connection successful!")
        # Example: Perform a simple query
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            db_version = cur.fetchone()
            print("PostgreSQL database version:", db_version)
        print("Returning connection to the pool.")
        return_db_connection(conn)
    else:
        print("Failed to get a database connection.")
