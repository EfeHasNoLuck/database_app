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

# Helper to fetch simplified user info
def get_user_info(user_id):
    conn = get_db_connection()
    user = None
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT first_name, last_name, email FROM User WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            print(f"Error fetching user data: {err}")
    return user

# --- Student Routes ---
@app.route('/student_dashboard')
def student_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user = get_user_info(session['user_id'])
    conn = get_db_connection()
    active_project = None
    activities = []
    
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            # 1. Fetch Active Project
            cursor.execute("SELECT student_id FROM Student WHERE user_id = %s", (session['user_id'],))
            student = cursor.fetchone()
            if student:
                query_project = """
                    SELECT P.title, P.status
                    FROM Project P
                    JOIN Selection Sel ON P.project_id = Sel.project_id
                    WHERE Sel.student_id = %s AND Sel.status = 'approved'
                """
                cursor.execute(query_project, (student['student_id'],))
                active_project = cursor.fetchone()
                
                # 2. Fetch Recent Activity (Mocking/Simulating from Submissions and Selection)
                # In a real app, you might have a dedicated Activity_Log table or complex union query
                # Here we'll just check for recent submissions and if they have a project selected
                
                # Selection Activity
                cursor.execute("""
                    SELECT 'check_circle' as icon, CONCAT('Project "', P.title, '" ', Sel.status) as text, Sel.status as type, 'Recently' as time
                    FROM Selection Sel
                    JOIN Project P ON Sel.project_id = P.project_id
                    WHERE Sel.student_id = %s
                    ORDER BY Sel.selection_id DESC LIMIT 1
                """, (student['student_id'],))
                selection_act = cursor.fetchone()
                if selection_act:
                    activities.append(selection_act)
                    
                # Submission Activity
                cursor.execute("""
                    SELECT 'upload_file' as icon, CONCAT('Submitted for "', T.title, '"') as text, 'submission' as type, S.submission_date as time
                    FROM Submission S
                    JOIN Task T ON S.task_id = T.task_id
                    WHERE S.student_id = %s
                    ORDER BY S.submission_date DESC LIMIT 5
                """, (student['student_id'],))
                submission_acts = cursor.fetchall()
                for act in submission_acts:
                    # Format time a bit if it's a datetime object, or let Jinja handle
                    activities.append(act)
                
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            print(f"Error fetching dashboard data: {err}")
            
    return render_template('student_dashboard.html', user=user, active_project=active_project, activities=activities)

@app.route('/student_projects')
def student_projects():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user = get_user_info(session['user_id'])
    conn = get_db_connection()
    projects = []
    selected_project_id = None
    
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            # Fetch all projects with supervisor names
            query = """
                SELECT P.*, U.first_name, U.last_name, S.title as sup_title
                FROM Project P
                JOIN Supervisor S ON P.supervisor_id = S.supervisor_id
                JOIN User U ON S.user_id = U.user_id
            """
            cursor.execute(query)
            projects = cursor.fetchall()
            
            # Check if student has a selection
            # First get student_id
            cursor.execute("SELECT student_id FROM Student WHERE user_id = %s", (session['user_id'],))
            student = cursor.fetchone()
            if student:
                cursor.execute("SELECT project_id FROM Selection WHERE student_id = %s", (student['student_id'],))
                selection = cursor.fetchone()
                if selection:
                    selected_project_id = selection['project_id']
            
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            print(f"Error fetching projects: {err}")
            
    return render_template('student_projects.html', user=user, projects=projects, selected_project_id=selected_project_id)

@app.route('/student_project_detail')
def student_project_detail():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user = get_user_info(session['user_id'])
    conn = get_db_connection()
    project = None
    tasks = []
    evaluations = []
    
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            # Get student's selected project
            cursor.execute("SELECT student_id FROM Student WHERE user_id = %s", (session['user_id'],))
            student = cursor.fetchone()
            
            if student:
                # Get selected project details
                query_project = """
                    SELECT P.*, U.first_name, U.last_name, S.title as sup_title, Sel.status as sel_status
                    FROM Project P
                    JOIN Selection Sel ON P.project_id = Sel.project_id
                    JOIN Supervisor S ON P.supervisor_id = S.supervisor_id
                    JOIN User U ON S.user_id = U.user_id
                    WHERE Sel.student_id = %s
                """
                cursor.execute(query_project, (student['student_id'],))
                project = cursor.fetchone()
                
                if project:
                    # Get tasks for this project
                    cursor.execute("SELECT * FROM Task WHERE project_id = %s ORDER BY deadline", (project['project_id'],))
                    tasks = cursor.fetchall()
                    
                    # Get evaluations for this student's submissions to these tasks
                    query_evals = """
                        SELECT E.grade, E.feedback, E.evaluation_date, T.title as task_title
                        FROM Evaluation E
                        JOIN Submission Sub ON E.submission_id = Sub.submission_id
                        JOIN Task T ON Sub.task_id = T.task_id
                        WHERE Sub.student_id = %s AND T.project_id = %s
                        ORDER BY E.evaluation_date DESC
                    """
                    cursor.execute(query_evals, (student['student_id'], project['project_id']))
                    evaluations = cursor.fetchall()
            
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            print(f"Error fetching project detail: {err}")
            
    return render_template('student_project_detail.html', user=user, project=project, tasks=tasks, evaluations=evaluations)

# --- Supervisor Routes ---
@app.route('/supervisor_dashboard')
def supervisor_dashboard():
    return render_template('supervisor_dashboard.html')

@app.route('/supervisor_project_detail')
def supervisor_project_detail():
    return render_template('supervisor_project_detail.html')

@app.route('/supervisor_evaluation')
def supervisor_evaluation():
    return render_template('supervisor_evaluation.html')

# --- Admin Routes ---
@app.route('/admin_dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/admin_users')
def admin_users():
    return render_template('admin_users.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
