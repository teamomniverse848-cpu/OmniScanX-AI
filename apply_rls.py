import os
import psycopg
from database.db_connector import get_db_connection

def apply_rls():
    db = get_db_connection()
    if not db:
        print("Failed to connect to the database.")
        return
    
    cursor = db.cursor()
    tables = ['departments', 'users', 'students', 'attendance', 'face_embeddings', 'class_sessions']
    
    try:
        for table in tables:
            cursor.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
            print(f"Enabled RLS on table: {table}")
        
        db.commit()
        print("Successfully enabled RLS on all tables.")
    except Exception as e:
        print(f"Error applying RLS: {e}")
        db.rollback()
    finally:
        cursor.close()
        db.close()

if __name__ == '__main__':
    apply_rls()
