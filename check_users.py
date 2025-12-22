import mysql.connector
from db_config import DB_CONFIG

def list_users():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        print("\n--- Registered Users in Database ---")
        cursor.execute("SELECT user_id, first_name, last_name, email, role FROM User")
        users = cursor.fetchall()
        
        if not users:
            print("No users found.")
        else:
            print(f"{'ID':<5} {'Name':<20} {'Email':<30} {'Role':<15}")
            print("-" * 75)
            for user in users:
                name = f"{user['first_name']} {user['last_name']}"
                print(f"{user['user_id']:<5} {name:<20} {user['email']:<30} {user['role']:<15}")
        
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"Error: {err}")

if __name__ == "__main__":
    list_users()
