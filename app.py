import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

from flask import Flask, render_template, request, redirect, url_for, session, flash
from config import Config
from database.db_connector import get_db_connection
from werkzeug.security import check_password_hash, generate_password_hash
import random
from psycopg.rows import dict_row
from flask_mail import Mail, Message
from authlib.integrations.flask_client import OAuth
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.config.from_object(Config)

# Initialize Flask-Mail
mail = Mail(app)

# Initialize OAuth
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    client_kwargs={'scope': 'openid email profile'},
    jwks_uri='https://www.googleapis.com/oauth2/v3/certs'
)

# ==========================================
# Authentication Routes
# ==========================================

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    db = get_db_connection()
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        department_id = request.form.get('department_id')
        role = request.form.get('role') # 'student' or 'teacher'
        
        if db:
            cursor = db.cursor(row_factory=dict_row)
            try:
                # Hash password
                hashed_pw = generate_password_hash(password)
                
                # Determine database role
                db_role = 'admin' if role == 'teacher' else 'student'
                
                # Insert into users table and return the new ID
                cursor.execute("""
                    INSERT INTO users (username, email, password_hash, role)
                    VALUES (%s, %s, %s, %s) RETURNING id
                """, (username, email, hashed_pw, db_role))
                
                new_user_id = cursor.fetchone()['id']
                
                # Insert into students table ONLY if they are a student
                if db_role == 'student':
                    cursor.execute("""
                        INSERT INTO students (user_id, first_name, last_name, email, department_id, enrollment_date)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_DATE)
                    """, (new_user_id, first_name, last_name, email, department_id))
                
                db.commit()
                flash('Account created successfully! Please log in.', 'success')
                return redirect(url_for('login'))
                
            except Exception as e:
                db.rollback()
                flash(f'Error creating account (Username or Email might already exist).', 'danger')
            finally:
                cursor.close()

    # GET request: fetch departments for the dropdown
    departments = []
    if db:
        cursor = db.cursor(row_factory=dict_row)
        cursor.execute("SELECT id, name FROM departments")
        departments = cursor.fetchall()
        
        # Auto-seed departments if empty so UI is never blank
        if not departments:
            cursor.execute("INSERT INTO departments (name) VALUES ('Computer Science'), ('Information Technology'), ('Data Science'), ('Software Engineering') ON CONFLICT DO NOTHING")
            db.commit()
            cursor.execute("SELECT id, name FROM departments")
            departments = cursor.fetchall()
            
        cursor.close()
        db.close()
        
    return render_template('signup.html', departments=departments)

@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        db = get_db_connection()
        if db:
            cursor = db.cursor(row_factory=dict_row)
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            
            # Use Werkzeug's check_password_hash
            if user and check_password_hash(user['password_hash'], password):
                # Generate OTP
                otp = str(random.randint(100000, 999999))
                
                # Store OTP and temporary user data in session
                session['pending_otp'] = otp
                session['pending_user_id'] = user['id']
                session['pending_username'] = user['username']
                session['pending_role'] = user['role']
                
                # Send OTP via Email (Requires real credentials in config.py)
                try:
                    if user.get('email'):
                        msg = Message('Your Login OTP', recipients=[user['email']])
                        msg.body = f'Your OTP for Attendance System is: {otp}'
                        mail.send(msg)
                        flash('An OTP has been sent to your registered email.', 'info')
                    else:
                        flash(f'Simulated OTP (No email configured): {otp}', 'info') # For local testing
                except Exception as e:
                    print("Mail error:", e)
                    flash(f'Simulated OTP for testing (Mail server not setup): {otp}', 'info')
                
                return redirect(url_for('verify_otp'))
            else:
                flash('Invalid email or password', 'danger')
            cursor.close()
            db.close()
        else:
            flash('Database connection failed', 'danger')
            
    return render_template('login.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if 'pending_otp' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        entered_otp = request.form.get('otp')
        if entered_otp == session.get('pending_otp'):
            # Clear pending session and log in user
            session.pop('pending_otp', None)
            session['user_id'] = session.pop('pending_user_id')
            session['username'] = session.pop('pending_username')
            session['role'] = session.pop('pending_role')
            
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid OTP. Please try again.', 'danger')
            
    return render_template('verify_otp.html')

@app.route('/login/google')
def login_google():
    # Generate the url for google oauth
    redirect_uri = url_for('auth_google', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/google')
def auth_google():
    token = google.authorize_access_token()
    user_info = google.get('userinfo').json()
    email = user_info.get('email')
    
    db = get_db_connection()
    if db:
        cursor = db.cursor(row_factory=dict_row)
        # Check if user exists by email
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash('Logged in successfully with Google.', 'success')
            cursor.close()
            db.close()
            return redirect(url_for('index'))
        else:
            session['google_email'] = email
            session['google_first_name'] = user_info.get('given_name', '')
            session['google_last_name'] = user_info.get('family_name', '')
            cursor.close()
            db.close()
            flash('Please complete your profile to continue.', 'info')
            return redirect(url_for('google_signup'))
            
    flash('Database connection failed', 'danger')
    return redirect(url_for('login'))

@app.route('/google_signup', methods=['GET', 'POST'])
def google_signup():
    if 'google_email' not in session:
        return redirect(url_for('login'))
        
    db = get_db_connection()
    if request.method == 'POST':
        email = session['google_email']
        first_name = request.form.get('first_name', session.get('google_first_name', ''))
        last_name = request.form.get('last_name', session.get('google_last_name', ''))
        department_id = request.form.get('department_id')
        role = request.form.get('role')
        password = request.form.get('password')
        
        if db:
            cursor = db.cursor(row_factory=dict_row)
            try:
                hashed_pw = generate_password_hash(password)
                db_role = 'admin' if role == 'teacher' else 'student'
                # Temporary username based on email
                username = email.split('@')[0] + str(random.randint(100, 999))
                
                cursor.execute("""
                    INSERT INTO users (username, email, password_hash, role)
                    VALUES (%s, %s, %s, %s) RETURNING id
                """, (username, email, hashed_pw, db_role))
                new_user_id = cursor.fetchone()['id']
                
                if db_role == 'student':
                    cursor.execute("""
                        INSERT INTO students (user_id, first_name, last_name, email, department_id, enrollment_date)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_DATE)
                    """, (new_user_id, first_name, last_name, email, department_id))
                
                db.commit()
                
                # Auto-login
                session.pop('google_email', None)
                session.pop('google_first_name', None)
                session.pop('google_last_name', None)
                
                session['user_id'] = new_user_id
                session['username'] = username
                session['role'] = db_role
                
                flash('Account created successfully!', 'success')
                return redirect(url_for('index'))
                
            except Exception as e:
                db.rollback()
                flash(f'Error completing setup (Email might already exist in another record): {str(e)}', 'danger')
            finally:
                cursor.close()
    
    departments = []
    if db:
        cursor = db.cursor(row_factory=dict_row)
        cursor.execute("SELECT id, name FROM departments")
        departments = cursor.fetchall()
        cursor.close()
        db.close()
        
    return render_template('google_signup.html', departments=departments, 
                           first_name=session.get('google_first_name', ''), 
                           last_name=session.get('google_last_name', ''), 
                           email=session.get('google_email', ''))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        db = get_db_connection()
        if db:
            cursor = db.cursor(row_factory=dict_row)
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            
            if user:
                otp = str(random.randint(100000, 999999))
                session['reset_otp'] = otp
                session['reset_user_id'] = user['id']
                
                try:
                    if user.get('email'):
                        msg = Message('Password Reset OTP', recipients=[user['email']])
                        msg.body = f'Your OTP to reset your password is: {otp}'
                        mail.send(msg)
                        flash('A password reset OTP has been sent to your registered email.', 'info')
                    else:
                        flash(f'Simulated OTP (No email configured): {otp}', 'info')
                except Exception as e:
                    print("Mail error:", e)
                    flash(f'Simulated OTP for testing (Mail server not setup): {otp}', 'info')
                    
                cursor.close()
                db.close()
                return redirect(url_for('reset_password'))
            else:
                flash('Email not found.', 'danger')
            cursor.close()
            db.close()
    return render_template('forgot_password.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_otp' not in session or 'reset_user_id' not in session:
        flash('Session expired. Please request a new OTP.', 'warning')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        user_otp = request.form.get('otp')
        new_password = request.form.get('new_password')
        
        if user_otp == session.get('reset_otp'):
            user_id = session.get('reset_user_id')
            db = get_db_connection()
            if db:
                cursor = db.cursor()
                hashed_pw = generate_password_hash(new_password)
                try:
                    cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s", (hashed_pw, user_id))
                    db.commit()
                    session.pop('reset_otp', None)
                    session.pop('reset_user_id', None)
                    flash('Password reset successfully. You can now log in.', 'success')
                    return redirect(url_for('login'))
                except Exception as e:
                    db.rollback()
                    flash(f'Error resetting password: {str(e)}', 'danger')
                finally:
                    cursor.close()
                    db.close()
        else:
            flash('Invalid OTP. Please try again.', 'danger')
            
    return render_template('reset_password.html')

# ==========================================
# Dashboards and Attendance Module
# ==========================================

import csv
from flask import Response
from datetime import datetime

@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))
        
    db = get_db_connection()
    recent_logs = []
    if db:
        cursor = db.cursor(row_factory=dict_row)
        query = """
            SELECT a.date, a.status, s.first_name, s.last_name 
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            ORDER BY a.date DESC LIMIT 10
        """
        cursor.execute(query)
        recent_logs = cursor.fetchall()
        cursor.close()
        db.close()
        
    return render_template('admin_dashboard.html', recent_logs=recent_logs)

@app.route('/admin/attendance', methods=['GET', 'POST'])
def mark_attendance():
    if session.get('role') != 'admin':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))
        
    db = get_db_connection()
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        date = request.form.get('date')
        status = request.form.get('status')
        admin_id = session.get('user_id')
        
        if db:
            cursor = db.cursor()
            try:
                cursor.execute("""
                    INSERT INTO attendance (student_id, date, status, marked_by)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (student_id, date) DO UPDATE 
                    SET status = EXCLUDED.status, marked_by = EXCLUDED.marked_by
                """, (student_id, date, status, admin_id))
                db.commit()
                flash('Attendance marked successfully.', 'success')
            except Exception as e:
                db.rollback()
                flash(f'Error marking attendance: {str(e)}', 'danger')
            cursor.close()

    students = []
    if db:
        cursor = db.cursor(row_factory=dict_row)
        cursor.execute("SELECT id, first_name, last_name FROM students")
        students = cursor.fetchall()
        cursor.close()
        db.close()
        
    return render_template('mark_attendance.html', students=students, today=datetime.today().strftime('%Y-%m-%d'))

@app.route('/admin/students')
def admin_students():
    if session.get('role') != 'admin':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))
        
    db = get_db_connection()
    students = []
    if db:
        cursor = db.cursor(row_factory=dict_row)
        cursor.execute("""
            SELECT s.id, s.first_name, s.last_name, s.email, d.name as department
            FROM students s
            JOIN departments d ON s.department_id = d.id
            ORDER BY s.last_name ASC
        """)
        students = cursor.fetchall()
        cursor.close()
        db.close()
        
    return render_template('admin_students.html', students=students)

@app.route('/admin/student/edit/<int:student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    if session.get('role') != 'admin':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))
        
    db = get_db_connection()
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        department_id = request.form.get('department_id')
        
        if db:
            cursor = db.cursor()
            try:
                cursor.execute("""
                    UPDATE students 
                    SET first_name = %s, last_name = %s, email = %s, department_id = %s
                    WHERE id = %s
                """, (first_name, last_name, email, department_id, student_id))
                db.commit()
                flash('Student details updated successfully.', 'success')
                return redirect(url_for('admin_students'))
            except Exception as e:
                db.rollback()
                flash(f'Error updating student: {str(e)}', 'danger')
            finally:
                cursor.close()

    # GET request
    student = None
    departments = []
    if db:
        cursor = db.cursor(row_factory=dict_row)
        cursor.execute("SELECT * FROM students WHERE id = %s", (student_id,))
        student = cursor.fetchone()
        
        cursor.execute("SELECT id, name FROM departments")
        departments = cursor.fetchall()
        cursor.close()
        db.close()
        
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('admin_students'))
        
    return render_template('admin_edit_student.html', student=student, departments=departments)

@app.route('/admin/departments')
def admin_departments():
    if session.get('role') != 'admin':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))
        
    db = get_db_connection()
    departments = []
    if db:
        cursor = db.cursor(row_factory=dict_row)
        # Fetch departments with student count
        cursor.execute("""
            SELECT d.name, COUNT(s.id) as student_count
            FROM departments d
            LEFT JOIN students s ON d.id = s.department_id
            GROUP BY d.id, d.name
            ORDER BY d.name ASC
        """)
        departments = cursor.fetchall()
        cursor.close()
        db.close()
        
    return render_template('admin_departments.html', departments=departments)

@app.route('/admin/export_attendance')
def export_attendance():
    if session.get('role') != 'admin':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))
        
    db = get_db_connection()
    if not db:
        flash('Database connection failed', 'danger')
        return redirect(url_for('admin_dashboard'))
        
    cursor = db.cursor(row_factory=dict_row)
    query = """
        SELECT a.date, s.first_name, s.last_name, d.name as department, a.status 
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        JOIN departments d ON s.department_id = d.id
        ORDER BY a.date DESC
    """
    cursor.execute(query)
    records = cursor.fetchall()
    cursor.close()
    db.close()

    # Generate CSV
    def generate():
        data = ['Date,First Name,Last Name,Department,Status']
        for row in records:
            data.append(f"{row['date']},{row['first_name']},{row['last_name']},{row['department']},{row['status']}")
        return '\n'.join(data)

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=attendance_report.csv"}
    )

@app.route('/student_dashboard')
def student_dashboard():
    if session.get('role') != 'student':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))
        
    db = get_db_connection()
    student_info = {}
    attendance_records = []
    
    if db:
        cursor = db.cursor(row_factory=dict_row)
        # Get student info
        cursor.execute("""
            SELECT s.first_name, s.last_name, s.email, s.enrollment_date, d.name as department_name
            FROM students s
            JOIN departments d ON s.department_id = d.id
            WHERE s.user_id = %s
        """, (session.get('user_id'),))
        student_info = cursor.fetchone()
        
        # Get attendance records
        if student_info:
            cursor.execute("""
                SELECT date, status FROM attendance 
                WHERE student_id = (SELECT id FROM students WHERE user_id = %s)
                ORDER BY date DESC
            """, (session.get('user_id'),))
            attendance_records = cursor.fetchall()
            
        cursor.close()
        db.close()
        
    if not student_info:
        student_info = {'first_name': 'Profile', 'last_name': 'Not Found', 'email': 'N/A', 'department_name': 'N/A', 'enrollment_date': 'N/A'}
        
    return render_template('student_dashboard.html', student=student_info, attendance_records=attendance_records)

import os
import json
from services.face_service import get_embedding, base64_to_image, recognize_faces_in_group

@app.route('/admin/enroll_face', methods=['GET', 'POST'])
def enroll_face():
    if session.get('role') != 'admin':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))
        
    db = get_db_connection()
    if request.method == 'POST':
        # Now expects a JSON payload
        data = request.get_json()
        if not data:
            return {'success': False, 'message': 'Invalid JSON data'}, 400
            
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        email = data.get('email')
        department_id = data.get('department_id')
        images = data.get('images', [])
        
        if not first_name or not last_name or not email or not images:
            return {'success': False, 'message': 'Missing required student details or images'}, 400
            
        if db:
            cursor = db.cursor(row_factory=dict_row)
            try:
                # 0. Check if email already exists
                cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
                if cursor.fetchone():
                    return {'success': False, 'message': 'Email already exists. Please use a different email.'}, 400

                # 1. Create User
                # Generate a temporary username
                username = f"{first_name.lower()}.{last_name.lower()}.{random.randint(1000,9999)}"
                hashed_pw = generate_password_hash('student123') # Default password
                
                cursor.execute("""
                    INSERT INTO users (username, email, password_hash, role)
                    VALUES (%s, %s, %s, 'student') RETURNING id
                """, (username, email, hashed_pw))
                new_user_id = cursor.fetchone()['id']
                
                # 2. Create Student
                cursor.execute("""
                    INSERT INTO students (user_id, first_name, last_name, email, department_id, enrollment_date)
                    VALUES (%s, %s, %s, %s, %s, CURRENT_DATE) RETURNING id
                """, (new_user_id, first_name, last_name, email, department_id))
                student_id = cursor.fetchone()['id']
                
                # 3. Process the 10 images to get multiple embeddings
                valid_embeddings = []
                
                for idx, img_data in enumerate(images):
                    temp_path = f"temp_enroll_{student_id}_{idx}.jpg"
                    base64_to_image(img_data, temp_path)
                    
                    embedding = get_embedding(temp_path)
                    
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                        
                    if embedding is not None:
                        valid_embeddings.append(embedding)
                        
                if not valid_embeddings:
                    # Rollback the user creation if no faces were found
                    db.rollback()
                    return {'success': False, 'message': 'No faces detected in any of the 10 captured images. Registration failed.'}, 400
                    
                # 4. Store the list of valid embeddings
                emb_json = json.dumps(valid_embeddings)
                cursor.execute("""
                    INSERT INTO face_embeddings (student_id, embedding)
                    VALUES (%s, %s)
                """, (student_id, emb_json))
                
                db.commit()
                return {'success': True, 'message': f'Student registered & enrolled successfully with {len(valid_embeddings)} angles!'}
            except Exception as e:
                db.rollback()
                return {'success': False, 'message': f'Database error (Email may already exist): {str(e)}'}, 500
            finally:
                cursor.close()
                
        return {'success': False, 'message': 'Database connection failed'}, 500

    # GET request
    departments = []
    if db:
        cursor = db.cursor(row_factory=dict_row)
        cursor.execute("SELECT id, name FROM departments")
        departments = cursor.fetchall()
        cursor.close()
        db.close()
        
    return render_template('admin_face_enroll.html', departments=departments)

@app.route('/admin/auto_attendance', methods=['GET', 'POST'])
def auto_attendance():
    if session.get('role') != 'admin':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))
        
    db = get_db_connection()
    if request.method == 'POST':
        faculty_name = request.form.get('faculty_name')
        class_name = request.form.get('class_name')
        batch = request.form.get('batch')
        section = request.form.get('section')
        department_id = request.form.get('department_id')
        image_data = request.form.get('image_data')
        date_str = request.form.get('date', datetime.today().strftime('%Y-%m-%d'))
        
        if not image_data:
            return {'success': False, 'message': 'Missing image data'}, 400
            
        temp_path = f"temp_group_{session.get('user_id')}.jpg"
        base64_to_image(image_data, temp_path)
        
        known_embeddings = {}
        if db:
            cursor = db.cursor(row_factory=dict_row)
            cursor.execute("SELECT student_id, embedding FROM face_embeddings")
            rows = cursor.fetchall()
            for row in rows:
                known_embeddings[row['student_id']] = row['embedding']
            
        if not known_embeddings:
            return {'success': False, 'message': 'No enrolled students in the database.'}, 400
            
        matched_students = recognize_faces_in_group(temp_path, known_embeddings)
        
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        if db and matched_students:
            cursor = db.cursor(row_factory=dict_row)
            try:
                # Create class session
                cursor.execute("""
                    INSERT INTO class_sessions (faculty_name, class_name, batch, section, department_id, date)
                    VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                """, (faculty_name, class_name, batch, section, department_id, date_str))
                session_id = cursor.fetchone()['id']
                
                # Mark attendance
                for student_id in matched_students:
                    cursor.execute("""
                        INSERT INTO attendance (student_id, date, status, marked_by, class_session_id)
                        VALUES (%s, %s, 'Present', %s, %s)
                        ON CONFLICT (student_id, date) DO UPDATE 
                        SET status = 'Present', marked_by = EXCLUDED.marked_by, class_session_id = EXCLUDED.class_session_id
                    """, (student_id, date_str, session.get('user_id'), session_id))
                db.commit()
                return {'success': True, 'message': f'Attendance marked for {len(matched_students)} students!', 'matched_count': len(matched_students)}
            except Exception as e:
                db.rollback()
                return {'success': False, 'message': f'DB Error: {str(e)}'}, 500
            finally:
                cursor.close()
                
        if not matched_students:
            return {'success': False, 'message': 'No registered students recognized in the image.'}, 200

    departments = []
    if db:
        cursor = db.cursor(row_factory=dict_row)
        cursor.execute("SELECT id, name FROM departments")
        departments = cursor.fetchall()
        cursor.close()
        db.close()
        
    return render_template('admin_auto_attendance.html', departments=departments, today=datetime.today().strftime('%Y-%m-%d'))

@app.route('/admin/weekly_report')
def weekly_report():
    if session.get('role') != 'admin':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('login'))
        
    db = get_db_connection()
    report_data = []
    if db:
        cursor = db.cursor(row_factory=dict_row)
        # Query to aggregate attendance by class session and student over the last 7 days
        query = """
            SELECT 
                cs.class_name, 
                cs.batch, 
                cs.section, 
                d.name as department,
                s.first_name, 
                s.last_name,
                COUNT(a.id) as days_present
            FROM class_sessions cs
            JOIN attendance a ON a.class_session_id = cs.id
            JOIN students s ON a.student_id = s.id
            JOIN departments d ON cs.department_id = d.id
            WHERE cs.date >= CURRENT_DATE - INTERVAL '7 days'
            AND a.status = 'Present'
            GROUP BY cs.class_name, cs.batch, cs.section, d.name, s.first_name, s.last_name
            ORDER BY cs.batch, d.name, cs.class_name, s.last_name
        """
        cursor.execute(query)
        report_data = cursor.fetchall()
        cursor.close()
        db.close()
        
    return render_template('admin_weekly_report.html', report_data=report_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
