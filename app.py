from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from db_config import DB_CONFIG

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this for production

# Database Connection
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None

# --- Routes ---

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        
        conn = get_db_connection()
        user = None
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)
                # Note: In production, verify hashed password instead of plain text comparison
                cursor.execute("SELECT * FROM User WHERE email = %s AND password = %s", (email, password))
                user = cursor.fetchone()
                cursor.close()
                conn.close()
            except mysql.connector.Error as err:
                 print(f"Login Error: {err}") # Log error for debugging

        if user:
            # Login Success
            session['user_id'] = user['user_id']
            session['user_email'] = user['email']
            session['role'] = user['role']
            session['first_name'] = user['first_name']
            
            # Check if the role selected in form matches the actual user role logic (optional, but good for UX)
            # For now, we trust the DB role and redirect based on it.
            db_role = user['role']
            
            if db_role == 'student':
                return redirect(url_for('student_dashboard'))
            elif db_role == 'supervisor':
                return redirect(url_for('supervisor_dashboard'))
            elif db_role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                 flash(f'Unknown role: {db_role}')
        else:
            flash('Invalid email or password')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Extract form data
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name', '') # Optional in some uis but good to have
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                # 1. Create User
                # Note: In production, password should be hashed!
                query_user = "INSERT INTO User (email, password, first_name, last_name, role) VALUES (%s, %s, %s, %s, %s)"
                cursor.execute(query_user, (email, password, first_name, last_name, role))
                user_id = cursor.lastrowid

                # 2. Create Role Specific Entry
                if role == 'student':
                    # Generate a dummy student no for demo
                    student_no = f"S{user_id:05d}" 
                    query_student = "INSERT INTO Student (user_id, student_no) VALUES (%s, %s)"
                    cursor.execute(query_student, (user_id, student_no))
                elif role == 'supervisor':
                    query_supervisor = "INSERT INTO Supervisor (user_id, title) VALUES (%s, 'Prof.')"
                    cursor.execute(query_supervisor, (user_id,))
                
                conn.commit()
                cursor.close()
                conn.close()
                flash('Registration successful! Please login.')
                return redirect(url_for('login'))
            except mysql.connector.Error as err:
                flash(f'Error: {err}')
                if conn: conn.close()
        else:
             flash('Database connection failed')

    return render_template('register.html')

# --- Student Routes ---
@app.route('/student_dashboard')
def student_dashboard():
    if 'role' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    current_project = None
    
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            # Find student_id
            cursor.execute("SELECT student_id FROM Student WHERE user_id = %s", (session['user_id'],))
            student = cursor.fetchone()
            
            if student:
                student_id = student['student_id']
                # Check for active selection
                query = """
                    SELECT p.title, p.description, p.project_id, s.status, s.selection_id
                    FROM Selection s
                    JOIN Project p ON s.project_id = p.project_id
                    WHERE s.student_id = %s AND s.status IN ('approved', 'pending')
                    LIMIT 1
                """
                cursor.execute(query, (student_id,))
                current_project = cursor.fetchone()
                
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            print(f"Error fetching dashboard data: {err}")
            
    return render_template('student_dashboard.html', current_project=current_project)

@app.route('/supervisor_dashboard')
def supervisor_dashboard():
    if 'role' not in session or session['role'] != 'supervisor':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    stats = {
        'active_projects': 0,
        'active_students': 0,
        'pending_reviews': 0
    }
    active_projects_list = []
    
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            # Get supervisor_id
            cursor.execute("SELECT supervisor_id FROM Supervisor WHERE user_id = %s", (session['user_id'],))
            sup = cursor.fetchone()
            
            if sup:
                supervisor_id = sup['supervisor_id']
                
                # Active Projects
                cursor.execute("SELECT COUNT(*) as count FROM Project WHERE supervisor_id = %s AND status = 'active'", (supervisor_id,))
                stats['active_projects'] = cursor.fetchone()['count']
                
                # Active Students (Students with approved selection in my projects)
                cursor.execute("""
                    SELECT COUNT(DISTINCT s.student_id) as count 
                    FROM Selection s
                    JOIN Project p ON s.project_id = p.project_id
                    WHERE p.supervisor_id = %s AND s.status = 'approved'
                """, (supervisor_id,))
                stats['active_students'] = cursor.fetchone()['count']
                
                # Pending Reviews (Submissions in my projects + pending selections?) 
                # For now, just pending evaluations (Submissions without evaluation) - Simplify to 0 or logic later
                # Let's count pending Selections for simplicity in this turn as "Action Required"
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM Selection s
                    JOIN Project p ON s.project_id = p.project_id
                    WHERE p.supervisor_id = %s AND s.status = 'pending'
                """, (supervisor_id,))
                stats['pending_reviews'] = cursor.fetchone()['count']

                # Active Projects List
                cursor.execute("SELECT * FROM Project WHERE supervisor_id = %s LIMIT 5", (supervisor_id,))
                active_projects_list = cursor.fetchall()
                
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
             print(f"Error fetching supervisor stats: {err}")

    return render_template('supervisor_dashboard.html', stats=stats, projects=active_projects_list)

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
