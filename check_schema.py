import mysql.connector
from db_config import DB_CONFIG

def check_schema():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("DESCRIBE Notification")
        columns = cursor.fetchall()
        print("NOTIFICATION TABLE:")
        for col in columns:
            print(col)
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    check_schema()
