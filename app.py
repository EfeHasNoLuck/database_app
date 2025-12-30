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
            # Check if role matches
            db_role = user['role']
            
            # Role translation for messages
            role_map = {
                'student': 'Student',
                'supervisor': 'Supervisor',
                'admin': 'Administrator'
            }
            
            if db_role != role:
                db_role_str = role_map.get(db_role, db_role)
                role_str = role_map.get(role, role)
                flash(f"This email belongs to a {db_role_str} account. You cannot login as {role_str}.", 'role_error')
            else:
                # Login Success
                session['user_id'] = user['user_id']
                session['user_email'] = user['email']
                session['role'] = user['role']
                session['first_name'] = user['first_name']
                
                if db_role == 'student':
                    return redirect(url_for('student_dashboard'))
                elif db_role == 'supervisor':
                    return redirect(url_for('supervisor_dashboard'))
                elif db_role == 'admin':
                    return redirect(url_for('admin_dashboard'))
                else:
                    flash(f'Unknown role: {db_role}', 'role_error')
        else:
            flash('Invalid email or password', 'auth_error')
    
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
                    department = request.form.get('department')
                    # Generate a dummy student no for demo
                    student_no = f"S{user_id:05d}" 
                    query_student = "INSERT INTO Student (user_id, student_no, department) VALUES (%s, %s, %s)"
                    cursor.execute(query_student, (user_id, student_no, department))
                elif role == 'supervisor':
                    title = request.form.get('title')
                    expertise = request.form.get('expertise')
                    query_supervisor = "INSERT INTO Supervisor (user_id, title, expertise) VALUES (%s, %s, %s)"
                    cursor.execute(query_supervisor, (user_id, title, expertise))
                
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
                    SELECT P.title, Sel.status as status
                    FROM Project P
                    JOIN Selection Sel ON P.project_id = Sel.project_id
                    WHERE Sel.student_id = %s AND Sel.status IN ('approved', 'pending')
                    ORDER BY Sel.selection_id DESC LIMIT 1
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

@app.route('/select_project', methods=['POST'])
def select_project():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    project_id = request.form.get('project_id')
    conn = get_db_connection()
    
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Get Student ID
            cursor.execute("SELECT student_id FROM Student WHERE user_id = %s", (session['user_id'],))
            student = cursor.fetchone()
            
            if student:
                # Check if already selected a project
                cursor.execute("SELECT selection_id FROM Selection WHERE student_id = %s", (student['student_id'],))
                existing_selection = cursor.fetchone()
                
                if existing_selection:
                    flash("You have already selected a project.")
                else:
                    # Create Selection
                    query = "INSERT INTO Selection (student_id, project_id, status) VALUES (%s, %s, 'pending')"
                    cursor.execute(query, (student['student_id'], project_id))
                    conn.commit()
                    flash("Project selected successfully! Waiting for supervisor approval.")
            
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            print(f"Error selecting project: {err}")
            flash(f"Error: {err}")
            
    return redirect(url_for('student_projects'))

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
                    # Get tasks with submission status
                    query_tasks = """
                        SELECT T.*, Sub.submission_id, Sub.file_path, Sub.submission_date
                        FROM Task T
                        LEFT JOIN Submission Sub ON T.task_id = Sub.task_id AND Sub.student_id = %s
                        WHERE T.project_id = %s 
                        ORDER BY T.deadline
                    """
                    cursor.execute(query_tasks, (student['student_id'], project['project_id']))
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

from werkzeug.utils import secure_filename
import os

UPLOAD_FOLDER = 'static/uploads'
# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/submit_task', methods=['POST'])
def submit_task():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    task_id = request.form.get('task_id')
    
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.referrer)
        
    file = request.files['file']
    
    if file.filename == '':
        flash('No selected file')
        return redirect(request.referrer)
        
    if file:
        filename = secure_filename(file.filename)
        # Append timestamp or user_id to filename to avoid collisions? keeping simple for now.
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)
        
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT student_id FROM Student WHERE user_id = %s", (session['user_id'],))
                student = cursor.fetchone()
                
                if student:
                    # Insert submission
                    # Note: You might want to check if submission already exists and UPDATE it instead, 
                    # OR allow multiple submissions. Schema doesn't enforce unique task_id per student, 
                    # but logic might imply one. I'll stick to INSERT for now, or update if exists?
                    # Let's check first.
                    
                    cursor.execute("SELECT submission_id FROM Submission WHERE student_id = %s AND task_id = %s", 
                                   (student['student_id'], task_id))
                    existing = cursor.fetchone()
                    
                    if existing:
                        # Update existing
                        query = "UPDATE Submission SET file_path = %s, submission_date = NOW() WHERE submission_id = %s"
                        cursor.execute(query, (filename, existing['submission_id']))
                        flash('Submission updated successfully!')
                    else:
                        # Insert new
                        query = "INSERT INTO Submission (task_id, student_id, file_path) VALUES (%s, %s, %s)"
                        cursor.execute(query, (task_id, student['student_id'], filename))
                        flash('Task submitted successfully!')
                        
                    conn.commit()
                
                cursor.close()
                conn.close()
            except mysql.connector.Error as err:
                print(f"Error submitting task: {err}")
                flash(f"Error: {err}")
                
    return redirect(url_for('student_project_detail'))

# --- Supervisor Routes ---
@app.route('/supervisor_dashboard')
def supervisor_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user = get_user_info(session['user_id'])
    conn = get_db_connection()
    pending_submissions = []
    project_count = 0
    student_count = 0
    projects = []
    
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Fetch Supervisor ID
            cursor.execute("SELECT supervisor_id FROM Supervisor WHERE user_id = %s", (session['user_id'],))
            supervisor_data = cursor.fetchone()
            
            if supervisor_data:
                supervisor_id = supervisor_data['supervisor_id']
                
                # 1. Project Count & List
                cursor.execute("""
                    SELECT project_id, title, status, description 
                    FROM Project 
                    WHERE supervisor_id = %s
                """, (supervisor_id,))
                projects = cursor.fetchall()
                project_count = len(projects)
                
                # 2. Student Count (Distinct students selected in these projects)
                # Assuming 'approved' selections count as active students
                if projects:
                   project_ids = [str(p['project_id']) for p in projects]
                   placeholders = ','.join(['%s'] * len(project_ids))
                   query_students = f"""
                       SELECT COUNT(DISTINCT student_id) as cnt 
                       FROM Selection 
                       WHERE project_id IN ({placeholders}) AND status = 'approved'
                   """
                   cursor.execute(query_students, tuple(project_ids))
                   res = cursor.fetchone()
                   student_count = res['cnt'] if res else 0

            # 3. Pending Submissions (Same as before)
            # Note: The query joins Supervisor table and filters by user_id so it's safe even without explicit supervisor_id above
            query_subs = """
                SELECT Sub.*, T.title as task_title, P.title as project_title, 
                       U.first_name, U.last_name, S.student_no
                FROM Submission Sub
                JOIN Task T ON Sub.task_id = T.task_id
                JOIN Project P ON T.project_id = P.project_id
                JOIN Supervisor Sup ON P.supervisor_id = Sup.supervisor_id
                JOIN Student S ON Sub.student_id = S.student_id
                JOIN User U ON S.user_id = U.user_id
                LEFT JOIN Evaluation E ON Sub.submission_id = E.submission_id
                WHERE Sup.user_id = %s AND E.evaluation_id IS NULL
                ORDER BY Sub.submission_date ASC
            """
            cursor.execute(query_subs, (session['user_id'],))
            pending_submissions = cursor.fetchall()
            
            # 4. Completed Evaluations (Recent 5)
            query_evals = """
                SELECT Sub.*, T.title as task_title, P.title as project_title,
                       U.first_name, U.last_name, S.student_no,
                       E.grade, E.feedback, E.evaluation_date
                FROM Submission Sub
                JOIN Task T ON Sub.task_id = T.task_id
                JOIN Project P ON T.project_id = P.project_id
                JOIN Supervisor Sup ON P.supervisor_id = Sup.supervisor_id
                JOIN Student S ON Sub.student_id = S.student_id
                JOIN User U ON S.user_id = U.user_id
                JOIN Evaluation E ON Sub.submission_id = E.submission_id
                WHERE Sup.user_id = %s
                ORDER BY E.evaluation_date DESC LIMIT 5
            """
            cursor.execute(query_evals, (session['user_id'],))
            completed_evaluations = cursor.fetchall()
            
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            print(f"Error fetching supervisor dashboard: {err}")
            
    return render_template('supervisor_dashboard.html', user=user, pending_submissions=pending_submissions, 
                           completed_evaluations=completed_evaluations,
                           project_count=project_count, student_count=student_count, projects=projects)

@app.route('/supervisor_create_project', methods=['GET', 'POST'])
def supervisor_create_project():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user = get_user_info(session['user_id'])
    conn = get_db_connection()
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)
                # Get Supervisor ID
                cursor.execute("SELECT supervisor_id FROM Supervisor WHERE user_id = %s", (session['user_id'],))
                supervisor = cursor.fetchone()
                
                if supervisor:
                    query = "INSERT INTO Project (title, description, status, supervisor_id) VALUES (%s, %s, 'active', %s)"
                    cursor.execute(query, (title, description, supervisor['supervisor_id']))
                    conn.commit()
                    flash(f"Project '{title}' created successfully!")
                    cursor.close()
                    conn.close()
                    return redirect(url_for('supervisor_dashboard'))
                else:
                    flash("Supervisor profile not found.")
                    
            except mysql.connector.Error as err:
                print(f"Error creating project: {err}")
                flash(f"Error creating project: {err}")
        else:
             flash("Database connection failed")
             
    return render_template('supervisor_create_project.html', user=user)


@app.route('/create_task', methods=['POST'])
def create_task():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    project_id = request.form.get('project_id')
    title = request.form.get('title')
    deadline = request.form.get('deadline')
    instruction = request.form.get('instruction')
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            
            # 1. Verify Supervisor Ownership
            cursor.execute("SELECT supervisor_id FROM Supervisor WHERE user_id = %s", (session['user_id'],))
            supervisor = cursor.fetchone()
            
            if supervisor:
                # Check if project belongs to this supervisor
                cursor.execute("SELECT project_id FROM Project WHERE project_id = %s AND supervisor_id = %s", 
                               (project_id, supervisor['supervisor_id']))
                project = cursor.fetchone()
                
                if project:
                    # 2. Create Task
                    query = "INSERT INTO Task (project_id, title, instruction, deadline) VALUES (%s, %s, %s, %s)"
                    cursor.execute(query, (project_id, title, instruction, deadline))
                    conn.commit()
                    flash(f"Task '{title}' created successfully!")
                else:
                    flash("Project not found or access denied.")
            else:
                flash("Supervisor profile not found.")
                
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            print(f"Error creating task: {err}")
            flash(f"Error creating task: {err}")
    
    return redirect(url_for('supervisor_project_detail', project_id=project_id))

@app.route('/supervisor_project_detail/<int:project_id>')
def supervisor_project_detail(project_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user = get_user_info(session['user_id'])
    conn = get_db_connection()
    project = None
    tasks = []
    students = []
    
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            
            # 1. Fetch Project Details & Verify Ownership
            # Join with Supervisor to check user_id
            query_proj = """
                SELECT P.*, S.title as sup_title
                FROM Project P
                JOIN Supervisor S ON P.supervisor_id = S.supervisor_id
                WHERE P.project_id = %s AND S.user_id = %s
            """
            cursor.execute(query_proj, (project_id, session['user_id']))
            project = cursor.fetchone()
            
            if not project:
                flash("Project not found or access denied.")
                return redirect(url_for('supervisor_projects'))
                
            # 2. Fetch Tasks
            cursor.execute("SELECT * FROM Task WHERE project_id = %s ORDER BY deadline", (project_id,))
            tasks = cursor.fetchall()
            
            # 3. Fetch Enrolled Students
            query_students = """
                SELECT S.student_no, U.first_name, U.last_name, U.email
                FROM Selection Sel
                JOIN Student S ON Sel.student_id = S.student_id
                JOIN User U ON S.user_id = U.user_id
                WHERE Sel.project_id = %s AND Sel.status = 'approved'
            """
            cursor.execute(query_students, (project_id,))
            students = cursor.fetchall()
            
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
             print(f"Error fetching project detail: {err}")
             flash(f"Error: {err}")
             
    return render_template('supervisor_project_detail.html', user=user, project=project, tasks=tasks, students=students)

@app.route('/supervisor_projects')
def supervisor_projects():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user = get_user_info(session['user_id'])
    conn = get_db_connection()
    projects = []
    
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT supervisor_id FROM Supervisor WHERE user_id = %s", (session['user_id'],))
            sup = cursor.fetchone()
            
            if sup:
                # Fetch projects with student counts and task counts
                query = """
                    SELECT P.*, 
                           (SELECT COUNT(*) FROM Selection WHERE project_id = P.project_id AND status='approved') as student_count,
                           (SELECT COUNT(*) FROM Task WHERE project_id = P.project_id) as task_count
                    FROM Project P
                    WHERE P.supervisor_id = %s
                """
                cursor.execute(query, (sup['supervisor_id'],))
                projects = cursor.fetchall()
                
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            print(f"Error fetching projects list: {err}")
            
    return render_template('supervisor_projects.html', user=user, projects=projects)

@app.route('/supervisor_evaluation/<int:submission_id>', methods=['GET', 'POST'])
def supervisor_evaluation(submission_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user = get_user_info(session['user_id'])    
    conn = get_db_connection()
    if request.method == 'POST':
        grade = request.form.get('grade')
        feedback = request.form.get('feedback')
        
        if conn:
            try:
                cursor = conn.cursor()
                query = "INSERT INTO Evaluation (submission_id, grade, feedback) VALUES (%s, %s, %s)"
                cursor.execute(query, (submission_id, grade, feedback))
                conn.commit()
                cursor.close()
                conn.close()
                flash('Evaluation submitted successfully!')
                return redirect(url_for('supervisor_dashboard'))
            except mysql.connector.Error as err:
                print(f"Error submitting evaluation: {err}")
                flash(f"Error: {err}")
    
    # GET request: Show form
    submission = None
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT Sub.*, T.title as task_title, P.title as project_title, 
                       U.first_name, U.last_name, S.student_no, Sup.user_id as supervisor_user_id
                FROM Submission Sub
                JOIN Task T ON Sub.task_id = T.task_id
                JOIN Project P ON T.project_id = P.project_id
                JOIN Supervisor Sup ON P.supervisor_id = Sup.supervisor_id
                JOIN Student S ON Sub.student_id = S.student_id
                JOIN User U ON S.user_id = U.user_id
                WHERE Sub.submission_id = %s
            """
            cursor.execute(query, (submission_id,))
            submission = cursor.fetchone()
            cursor.close()
            conn.close()
            
            # Security check: Ensure the logged-in supervisor owns this project
            if submission and submission['supervisor_user_id'] != session.get('user_id'):
                 flash("You do not have permission to evaluate this submission.")
                 return redirect(url_for('supervisor_dashboard'))
                 
        except mysql.connector.Error as err:
            print(f"Error fetching submission for evaluation: {err}")

    return render_template('supervisor_evaluation.html', user=user, submission=submission)

@app.route('/supervisor_evaluations')
def supervisor_evaluations():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user = get_user_info(session['user_id'])
    conn = get_db_connection()
    pending_submissions = []
    
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            # Fetch pending submissions only
            query = """
                SELECT Sub.*, T.title as task_title, P.title as project_title, 
                       U.first_name, U.last_name, S.student_no, Sup.user_id as supervisor_user_id
                FROM Submission Sub
                JOIN Task T ON Sub.task_id = T.task_id
                JOIN Project P ON T.project_id = P.project_id
                JOIN Supervisor Sup ON P.supervisor_id = Sup.supervisor_id
                JOIN Student S ON Sub.student_id = S.student_id
                JOIN User U ON S.user_id = U.user_id
                LEFT JOIN Evaluation E ON Sub.submission_id = E.submission_id
                WHERE Sup.user_id = %s AND E.evaluation_id IS NULL
                ORDER BY Sub.submission_date ASC
            """
            cursor.execute(query, (session['user_id'],))
            pending_submissions = cursor.fetchall()
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            print(f"Error fetching evaluations list: {err}")
            
    return render_template('supervisor_evaluations.html', user=user, pending_submissions=pending_submissions)

# --- Admin Routes ---
@app.route('/admin_dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/admin_users')
def admin_users():
    return render_template('admin_users.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
