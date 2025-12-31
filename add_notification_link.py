import mysql.connector
from db_config import DB_CONFIG

def migrate_db():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 1. Add column if not exists
        try:
            cursor.execute("ALTER TABLE Notification ADD COLUMN related_link VARCHAR(255) DEFAULT NULL")
            print("COLUMN_ADDED: related_link")
        except mysql.connector.Error as err:
            if "Duplicate column" in str(err):
                print("COLUMN_EXISTS: related_link")
            else:
                print(f"ALTER_ERROR: {err}")

        # 2. Update existing notifications with dummy links
        # Link project notifications to a generic project page for now
        cursor.execute("UPDATE Notification SET related_link = '/student_dashboard' WHERE related_link IS NULL")
        print("DATA_UPDATED: Existing notifications linked to dashboard")
        
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    migrate_db()
