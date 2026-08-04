import psycopg
from config import Config

def get_db_connection():
    """Establishes and returns a PostgreSQL database connection."""
    try:
        connection = psycopg.connect(Config.SUPABASE_DB_URL)
        return connection
    except Exception as e:
        print(f"Error while connecting to PostgreSQL (Supabase): {e}")
        return None
