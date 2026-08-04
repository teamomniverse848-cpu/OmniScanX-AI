import os
from config import Config
from database.db_connector import get_db_connection

def apply_schema():
    db = get_db_connection()
    if db:
        cursor = db.cursor()
        with open('database/schema.sql', 'r') as f:
            sql = f.read()
        try:
            cursor.execute(sql)
            db.commit()
            print("Schema applied successfully!")
        except Exception as e:
            print(f"Error applying schema: {e}")
        finally:
            cursor.close()
            db.close()
    else:
        print("Could not connect to database.")

if __name__ == '__main__':
    apply_schema()
