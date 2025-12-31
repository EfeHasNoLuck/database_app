import mysql.connector
from db_config import DB_CONFIG

def check_user():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM User WHERE email = 'frank@edu.com'")
        user = cursor.fetchone()
        
        print(f"USER: {user}")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    check_user()
