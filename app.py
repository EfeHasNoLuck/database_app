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
    # TODO: Fetch real data
    return render_template('student_dashboard.html')

@app.route('/student_projects')
def student_projects():
    return render_template('student_projects.html')

@app.route('/student_project_detail')
def student_project_detail():
    return render_template('student_project_detail.html')

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
