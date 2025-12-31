import mysql.connector
from db_config import DB_CONFIG
import re

def parse_sql_file(filename):
    with open(filename, 'r') as f:
        content = f.read()
    # Remove comments
    content = re.sub(r'--.*', '', content)
    # Split by semicolon
    commands = content.split(';')
    return [cmd.strip() for cmd in commands if cmd.strip()]

def init_and_seed():
    print("Connecting to MySQL Server...")
    # 1. Connect without Database to create it
    config_no_db = DB_CONFIG.copy()
    db_name = config_no_db.pop('database')
    
    try:
        conn = mysql.connector.connect(**config_no_db)
        cursor = conn.cursor()
        
        print(f"Creating database '{db_name}' if not exists...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        cursor.execute(f"USE {db_name}")
        
        # 2. Execute Schema
        print("Executing schema.sql...")
        commands = parse_sql_file('schema.sql')
        for cmd in commands:
            # Skip CREATE DATABASE / USE as we did it manually or it's handled
            if cmd.upper().startswith("CREATE DATABASE") or cmd.upper().startswith("USE"):
                continue
            # Skip SELECT statements (diagnostics in schema.sql)
            if cmd.strip().upper().startswith("SELECT"):
                continue
            try:
                cursor.execute(cmd)
            except mysql.connector.Error as err:
                print(f"Schema Warning (might be expected): {err}\nCommand: {cmd[:50]}...")
        
        conn.commit()
        
        # 3. Seed Data
        # Students Data
        students = [
            ("Alice", "Smith", "alice@edu.com", "password123", "S2023001", "Computer Engineering"),
            ("Bob", "Johnson", "bob@edu.com", "password123", "S2023002", "Electrical Engineering"),
            ("Charlie", "Brown", "charlie@edu.com", "password123", "S2023003", "Computer Engineering"),
            ("Diana", "Prince", "diana@edu.com", "password123", "S2023004", "Industrial Engineering"),
            ("Evan", "Wright", "evan@edu.com", "password123", "S2023005", "Software Engineering")
        ]

        # Supervisors Data
        supervisors = [
            ("Dr. Frank", "Einstein", "frank@edu.com", "password123", "Professor", "Artificial Intelligence"),
            ("Dr. Grace", "Hopper", "grace@edu.com", "password123", "Associate Prof", "Compilers & Languages"),
            ("Dr. Hank", "Pym", "hank@edu.com", "password123", "Assistant Prof", "Quantum Computing"),
            ("Dr. Iris", "West", "iris@edu.com", "password123", "Lecturer", "Data Science"),
            ("Dr. Jack", "Napier", "jack@edu.com", "password123", "Professor", "Cyber Security")
        ]

        print("Seeding Students...")
        for first, last, email, pwd, s_no, dept in students:
            cursor.execute("SELECT user_id FROM User WHERE email = %s", (email,))
            if cursor.fetchone():
                print(f"User {email} already exists. Skipping.")
                continue

            cursor.execute(
                "INSERT INTO User (email, password, first_name, last_name, role) VALUES (%s, %s, %s, %s, 'student')",
                (email, pwd, first, last)
            )
            user_id = cursor.lastrowid
            
            cursor.execute(
                "INSERT INTO Student (user_id, student_no, department) VALUES (%s, %s, %s)",
                (user_id, s_no, dept)
            )
            print(f"Created Student: {first} {last}")

        print("Seeding Supervisors...")
        for first, last, email, pwd, title, exp in supervisors:
            cursor.execute("SELECT user_id FROM User WHERE email = %s", (email,))
            if cursor.fetchone():
                print(f"User {email} already exists. Skipping.")
                continue

            cursor.execute(
                "INSERT INTO User (email, password, first_name, last_name, role) VALUES (%s, %s, %s, %s, 'supervisor')",
                (email, pwd, first, last)
            )
            user_id = cursor.lastrowid
            
            cursor.execute(
                "INSERT INTO Supervisor (user_id, title, expertise) VALUES (%s, %s, %s)",
                (user_id, title, exp)
            )
            print(f"Created Supervisor: {first} {last}")

        # --- Projects & Selections ---
        print("Seeding Projects...")
        # Get Supervisor (Dr. Frank)
        cursor.execute("SELECT supervisor_id FROM Supervisor LIMIT 1")
        sup = cursor.fetchone()
        if sup:
            sup_id = sup[0]
            # Create Project
            cursor.execute("""
                INSERT INTO Project (title, description, status, supervisor_id)
                VALUES (%s, %s, 'active', %s)
            """, ("AI-Driven Traffic Management System", "Using Deep Learning to optimize city traffic lights.", sup_id))
            project_id = cursor.lastrowid
            print("Created Project: AI-Driven Traffic Management System")

            # Get Student (Alice)
            cursor.execute("""
                SELECT s.student_id, u.user_id 
                FROM Student s 
                JOIN User u ON s.user_id = u.user_id 
                WHERE u.email = 'alice@edu.com'
            """)
            student = cursor.fetchone()
            
            if student:
                student_id, user_id = student
                # Create Selection (Approved)
                cursor.execute("""
                    INSERT INTO Selection (student_id, project_id, status)
                    VALUES (%s, %s, 'approved')
                """, (student_id, project_id))
                print("Assigned Project to Alice.")

                # Create Notification
                cursor.execute("""
                    INSERT INTO Notification (user_id, title, message)
                    VALUES (%s, %s, %s)
                """, (user_id, "Project Approved", "Your project 'AI-Driven Traffic Management' has been approved. Deadline: 2026-06-01."))

        conn.commit()

        # Seed Notifications (for testing)
        print("Seeding Notifications...")
        cursor.execute("SELECT user_id FROM User LIMIT 1")
        user = cursor.fetchone()
        if user:
            uid = user[0]
            cursor.execute("INSERT INTO Notification (user_id, title, message) VALUES (%s, %s, %s)", 
                           (uid, "Welcome!", "Welcome to the new system."))
            cursor.execute("INSERT INTO Notification (user_id, title, message) VALUES (%s, %s, %s)", 
                           (uid, "Project Deadline", "Don't forget the upcoming deadline."))

        conn.commit()
        print("Database Initialization and Seeding Completed Successfully!")
        cursor.close()
        conn.close()

    except mysql.connector.Error as err:
        print(f"Database Error: {err}")

if __name__ == "__main__":
    init_and_seed()
