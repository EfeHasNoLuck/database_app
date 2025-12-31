import mysql.connector
from db_config import DB_CONFIG

def check_and_create_admin():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM User WHERE role = 'admin'")
        admin = cursor.fetchone()
        
        if admin:
            print(f"ADMIN_FOUND: {admin['email']}")
        else:
            print("ADMIN_NOT_FOUND. Creating...")
            cursor.execute("""
                INSERT INTO User (email, password, first_name, last_name, role)
                VALUES ('admin@edu.com', 'admin123', 'System', 'Admin', 'admin')
            """)
            conn.commit()
            print("ADMIN_CREATED: admin@edu.com / admin123")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    check_and_create_admin()
