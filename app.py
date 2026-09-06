import sqlite3
import re
from flask import Flask, render_template, request, redirect, url_for, session, flash, render_template_string, jsonify

app = Flask(__name__)
app.secret_key = 'super_secret_college_erp_key'

def init_db():
    conn = sqlite3.connect('college_erp_final.db')
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT, role TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS students 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT, class_name TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS faculty 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT, department TEXT)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS attendance 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, date TEXT, status TEXT, 
                         subject TEXT, lecture TEXT, faculty_name TEXT)''')
                         
    cursor.execute('''CREATE TABLE IF NOT EXISTS marks 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, subject TEXT, 
                         cie_theory INTEGER, ese_theory INTEGER, 
                         cie_practical INTEGER, ese_practical INTEGER)''')
    
    cursor.execute("SELECT * FROM users WHERE role='admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                        ('admin@college.com', 'admin123', 'admin'))
        
    conn.commit()
    conn.close()

init_db()

# --- MOBILE APP API LOGIN ROUTE (Naya Joda gaya hai taaki phone login kaam kare) ---


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    conn = sqlite3.connect('college_erp_final.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # अपने डेटाबेस के हिसाब से टेबल और कॉलम का नाम चेक कर लें (जैसे users, email, password, role)
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        # अगर पासवर्ड चेक करने के लिए werkzeug का hash इस्तेमाल हो रहा है:
        from werkzeug.security import check_password_hash
        if check_password_hash(user['password'], password):
            return jsonify({
                "success": True,
                "role": user['role'],   
                "name": user['name']
            }), 200

    return jsonify({"success": False, "message": "Invalid email or password"}), 401

@app.route('/', methods=['GET', 'POST'])
@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role=None):
    if not role:
        role = 'student'
        
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        form_role = request.form.get('role', role)
        
        conn = sqlite3.connect('college_erp_final.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=? AND password=? AND role=?", (email, password, form_role))
        user = cursor.fetchone()
        
        if user:
            session['user'] = email
            session['role'] = form_role
            
            if form_role == 'faculty':
                cursor.execute("SELECT name FROM faculty WHERE email=?", (email,))
                faculty_data = cursor.fetchone()
                if faculty_data:
                    session['user_name'] = faculty_data[0]
                else:
                    session['user_name'] = "Faculty Member"
            
            conn.close()
            if form_role == 'admin': 
                return redirect(url_for('admin_dashboard'))
            elif form_role == 'faculty': 
                return redirect(url_for('faculty_dashboard'))
            else: 
                return redirect(url_for('student_dashboard'))
        else:
            if 'conn' in locals(): conn.close()
            flash(f"Invalid email or password for {form_role}.", "danger")
            
    return render_template('login.html', role=role)

@app.route('/signup/<role>', methods=['GET', 'POST'])
def signup(role):
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect('college_erp_final.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=? AND role=?", (email, role))
        if cursor.fetchone():
            flash("Email already registered for this role. Please log in.", "warning")
            conn.close()
            return redirect(url_for('signup', role=role))
            
        if role == 'student':
            class_name = request.form['class_name']
            cursor.execute("INSERT INTO students (name, email, class_name) VALUES (?, ?, ?)", (name, email, class_name))
        elif role == 'faculty':
            department = request.form['department']
            cursor.execute("INSERT INTO faculty (name, email, department) VALUES (?, ?, ?)", (name, email, department))
            
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (email, password, role))
        conn.commit()
        conn.close()
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for('login', role=role))
    return render_template('signup.html', role=role)

@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login', role='student'))
        
    conn = sqlite3.connect('college_erp_final.db')
    cursor = conn.cursor()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'single_student':
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            class_name = request.form.get('class_name')
            cursor.execute("INSERT INTO students (name, email, class_name) VALUES (?, ?, ?)", (name, email, class_name))
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'student')", (email, password))
            flash("New student added successfully.", "success")
            conn.commit()
            
        elif action == 'bulk_student':
            class_name = request.form.get('class_name')
            pdf_text = request.form.get('pdf_text')
            
            if not pdf_text or not pdf_text.strip():
                flash("0 students extracted. PDF did not contain readable text.", "danger")
            else:
                try:
                    success_count = 0
                    name_pattern = re.compile(r'\d+\s+([A-Za-z][A-Za-z\s]+?)(?=\s+\d+|\s*$|\n)')
                    extracted_names = name_pattern.findall(pdf_text)
                    
                    if not extracted_names:
                        lines = pdf_text.split('\n')
                        for line in lines:
                            line = line.strip()
                            if len(line) > 3 and not line.isdigit():
                                extracted_names.append(line)

                    for name in extracted_names:
                        name = name.strip()
                        if "student name" in name.lower() or "roll no" in name.lower() or len(name) < 3:
                            continue
                            
                        clean_name_for_email = name.lower().replace(" ", ".")
                        email = f"{clean_name_for_email}@college.com"
                        final_name = name.title()
                        default_password = "Student123"
                        
                        try:
                            cursor.execute("SELECT username FROM users WHERE username=?", (email,))
                            if not cursor.fetchone():
                                cursor.execute("INSERT INTO students (name, email, class_name) VALUES (?, ?, ?)", (final_name, email, class_name))
                                cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (email, default_password, 'student'))
                                success_count += 1
                        except Exception:
                            continue
                            
                    conn.commit()
                    if success_count > 0:
                        flash(f"Successfully extracted {success_count} students!", "success")
                except Exception as e:
                    flash(f"Error processing data: {str(e)}", "danger")

        elif action == 'single_faculty':
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            department = request.form.get('department')
            cursor.execute("INSERT INTO faculty (name, email, department) VALUES (?, ?, ?)", (name, email, department))
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'faculty')", (email, password))
            flash("New faculty added successfully.", "success")
            conn.commit()

    cursor.execute("SELECT * FROM students")
    students = cursor.fetchall()
    cursor.execute("SELECT * FROM faculty")
    faculties = cursor.fetchall()
    conn.close()
    return render_template('admin_dashboard.html', students=students, faculties=faculties)

@app.route('/faculty_dashboard', methods=['GET', 'POST'])
def faculty_dashboard():
    if 'role' not in session or session['role'] != 'faculty':
        return redirect(url_for('login', role='faculty'))
        
    conn = sqlite3.connect('college_erp_final.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT DISTINCT class_name FROM students")
    classes = [row[0] for row in cursor.fetchall()]
    
    subjects_list = ["Python Programming", "Database Management (DBMS)", "Web Technology", "Data Structures (DSA)", "Mathematics", "Computer Networks"]
    
    lectures_list = [
        {"id": "L1", "name": "Lecture 1"},
        {"id": "L2", "name": "Lecture 2"},
        {"id": "L3", "name": "Lecture 3"},
        {"id": "L4", "name": "Lecture 4"},
        {"id": "L5", "name": "Lecture 5"}
    ]
    
    selected_class = request.args.get('class_name')
    selected_subject = request.args.get('subject') 
    selected_lecture = request.args.get('lecture') 
    marks_mode = request.args.get('marks_mode')
    students = []
    
    if selected_class:
        cursor.execute('''
            SELECT s.id, s.name, s.email, IFNULL(m.cie_theory, 0), IFNULL(m.cie_practical, 0)
            FROM students s
            LEFT JOIN marks m ON LOWER(s.email) = LOWER(m.email) AND m.subject = ?
            WHERE s.class_name = ?
        ''', (selected_subject, selected_class))
        students = cursor.fetchall()
        
    conn.close()
    faculty_name = session.get('user_name', 'Faculty')
    
    return render_template('faculty_dashboard.html', 
                           classes=classes, 
                           subjects_list=subjects_list, 
                           lectures_list=lectures_list,
                           selected_class=selected_class, 
                           selected_subject=selected_subject, 
                           selected_lecture=selected_lecture, 
                           students=students,
                           faculty_name=faculty_name,
                           marks_mode=marks_mode)

@app.route('/save_attendance', methods=['POST'])
def save_attendance():
    if 'role' not in session or session['role'] != 'faculty':
        return redirect(url_for('login', role='faculty'))
        
    class_name = request.form.get('class_name')
    subject = request.form.get('subject') 
    lecture = request.form.get('lecture') 
    date = request.form.get('date')
    current_faculty_name = session.get('user_name', 'Faculty Member')
    
    conn = sqlite3.connect('college_erp_final.db')
    cursor = conn.cursor()
    
    for key, value in request.form.items():
        if key.startswith('attendance_'):
            student_email = key.replace('attendance_', '')
            status = value  
            
            cursor.execute("SELECT id FROM attendance WHERE email=? AND date=? AND subject=? AND lecture=?", 
                           (student_email, date, subject, lecture))
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute("UPDATE attendance SET status=?, faculty_name=? WHERE id=?", (status, current_faculty_name, existing[0]))
            else:
                cursor.execute('''INSERT INTO attendance (email, date, status, subject, lecture, faculty_name) 
                                  VALUES (?, ?, ?, ?, ?, ?)''', 
                               (student_email, date, status, subject, lecture, current_faculty_name))
                
    conn.commit()
    conn.close()
    flash("Attendance saved!", "success")
    return redirect(url_for('faculty_dashboard', class_name=class_name, subject=subject, lecture=lecture))

@app.route('/save_marks', methods=['POST'])
def save_marks():
    if 'role' not in session or session['role'] != 'faculty':
        return redirect(url_for('login', role='faculty'))
        
    class_name = request.form.get('class_name')
    subject = request.form.get('subject')
    
    conn = sqlite3.connect('college_erp_final.db')
    cursor = conn.cursor()
    
    for key in request.form.keys():
        if key.startswith('cie_theory_'):
            student_email = key.replace('cie_theory_', '')
            cie_theory = int(request.form.get(f'cie_theory_{student_email}', 0) or 0)
            cie_practical = int(request.form.get(f'cie_practical_{student_email}', 0) or 0)
            
            cursor.execute("SELECT id FROM marks WHERE LOWER(email)=? AND subject=?", (student_email.lower(), subject))
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute('''UPDATE marks SET cie_theory=?, cie_practical=? 
                                  WHERE id=?''', (cie_theory, cie_practical, existing[0]))
            else:
                cursor.execute('''INSERT INTO marks (email, subject, cie_theory, ese_theory, cie_practical, ese_practical) 
                                  VALUES (?, ?, ?, 0, ?, 0)''', (student_email, subject, cie_theory, cie_practical))
                            
    conn.commit()
    conn.close()
    flash("Marks successfully saved and updated! ✨", "success")
    return redirect(url_for('faculty_dashboard', class_name=class_name, subject=subject, marks_mode='yes'))

@app.route('/bulk_upload_marks', methods=['POST'])
def bulk_upload_marks():
    if 'role' not in session or session['role'] != 'faculty':
        return redirect(url_for('login', role='faculty'))
        
    class_name = request.form.get('class_name')
    subject = request.form.get('subject')
    upload_type = request.form.get('upload_type')
    
    raw_text = ""
    
    if upload_type == 'file':
        file = request.files.get('pdf_file_marks')
        if file and file.filename.endswith('.pdf'):
            try:
                with pdfplumber.open(file) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            raw_text += page_text + "\n"
            except Exception as e:
                flash(f"PDF Reading Error: {str(e)}", "danger")
                return redirect(url_for('faculty_dashboard', class_name=class_name, subject=subject, marks_mode='yes'))
        else:
            flash("Please upload a valid PDF file!", "danger")
            return redirect(url_for('faculty_dashboard', class_name=class_name, subject=subject, marks_mode='yes'))
            
    else:
        raw_text = request.form.get('pdf_text_marks', '')

    if not raw_text.strip():
        flash("No readable text found in PDF or Textbox!", "warning")
        return redirect(url_for('faculty_dashboard', class_name=class_name, subject=subject, marks_mode='yes'))

    conn = sqlite3.connect('college_erp_final.db')
    cursor = conn.cursor()
    
    lines = raw_text.split('\n')
    matched_count = 0
    
    cursor.execute("SELECT id, name, email FROM students WHERE class_name=?", (class_name,))
    students_in_db = cursor.fetchall()

    for line in lines:
        if not line.strip():
            continue
            
        numbers = re.findall(r'\b\d+\b', line)
        
        if len(numbers) >= 2: 
            cie_th = int(numbers[0])
            cie_pr = int(numbers[1])
            ese_th = int(numbers[2]) if len(numbers) > 2 else 0
            ese_pr = int(numbers[3]) if len(numbers) > 3 else 0
            
            for s_id, s_name, s_email in students_in_db:
                if s_name.lower() in line.lower() or s_email.lower() in line.lower():
                    
                    cursor.execute("SELECT id FROM marks WHERE LOWER(email)=? AND subject=?", (s_email.lower(), subject))
                    existing = cursor.fetchone()
                    
                    if existing:
                        cursor.execute('''UPDATE marks SET cie_theory=?, ese_theory=?, cie_practical=?, ese_practical=? 
                                           WHERE id=?''', (cie_th, ese_th, cie_pr, ese_pr, existing[0]))
                    else:
                        cursor.execute('''INSERT INTO marks (email, subject, cie_theory, ese_theory, cie_practical, ese_practical) 
                                           VALUES (?, ?, ?, ?, ?, ?)''', (s_email, subject, cie_th, ese_th, cie_pr, ese_pr))
                    matched_count += 1
                    break 
                
    conn.commit()
    conn.close()
    
    if matched_count > 0:
        flash(f"Successfully imported marks for {matched_count} students! 🚀", "success")
    else:
        flash("PDF read successfully, but no student names matched. Please check PDF format!", "sys-warning")
        
    return redirect(url_for('faculty_dashboard', class_name=class_name, subject=subject, marks_mode='yes'))

@app.route('/generate_pdf')
def generate_pdf():
    if 'role' not in session or session['role'] != 'faculty':
        return redirect(url_for('login', role='faculty'))
        
    class_name = request.args.get('class_name')
    subject = request.args.get('subject')
    faculty_name = session.get('user_name', 'Faculty Member')
    
    if not class_name or not subject:
        flash("Missing Class or Subject to generate PDF.", "danger")
        return redirect(url_for('faculty_dashboard'))
        
    conn = sqlite3.connect('college_erp_final.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name, email FROM students WHERE class_name=?", (class_name,))
    students = cursor.fetchall()
    
    report_data = []
    for std in students:
        std_id, std_name, std_email = std
        
        cursor.execute('''
            SELECT m.cie_theory, m.ese_theory, m.cie_practical, m.ese_practical 
            FROM marks m
            LEFT JOIN students s ON LOWER(s.email) = LOWER(m.email)
            WHERE (LOWER(m.email) = ? OR LOWER(s.name) = ?) AND m.subject = ?
        ''', (std_email.lower(), std_name.lower(), subject))
        
        row = cursor.fetchone()
        
        if row:
            cie_t, ese_t, cie_p, ese_p = row
        else:
            cie_t, ese_t, cie_p, ese_p = 0, 0, 0, 0
            
        total_marks = cie_t + ese_t + cie_p + ese_p
        
        report_data.append({
            "name": std_name,
            "email": std_email,
            "cie_t": cie_t,
            "ese_t": ese_t,
            "cie_p": cie_p,
            "ese_p": ese_p,
            "total": total_marks
        })
        
    conn.close()
    
    pdf_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Marksheet_{{ class_name }}_{{ subject }}</title>
        <style>
            body { font-family: 'Arial', sans-serif; margin: 30px; color: #333; background-color: #fff; }
            .header { text-align: center; border-bottom: 3px double #1e3a8a; padding-bottom: 15px; margin-bottom: 30px; }
            .header h1 { margin: 0; color: #1e3a8a; font-size: 26px; text-transform: uppercase; }
            .header h3 { margin: 5px 0 0 0; color: #555; font-weight: normal; }
            .meta-table { width: 100%; margin-bottom: 25px; font-size: 14px; border-collapse: collapse; }
            .meta-table td { padding: 6px 0; }
            .meta-label { font-weight: bold; color: #1e3a8a; width: 15%; }
            .meta-value { width: 35%; }
            .marks-table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
            .marks-table th, .marks-table td { border: 1px solid #cbd5e1; padding: 10px; text-align: center; }
            .marks-table th { background-color: #f1f5f9; color: #1e3a8a; font-weight: bold; }
            .text-start { text-align: left !important; }
            @media print { .no-print { display: none; } body { margin: 15px; } }
            .print-btn-container { text-align: right; margin-bottom: 20px; }
            .btn-print { background-color: #16a34a; color: white; border: none; padding: 10px 20px; font-size: 14px; font-weight: bold; border-radius: 6px; cursor: pointer; }
            .sign-box { border-top: 1px dashed #333; width: 200px; text-align: center; padding-top: 5px; margin-top: 40px; }
        </style>
    </head>
    <body>
        <div class="print-btn-container no-print">
            <button class="btn-print" onclick="window.print()">📥 Click Here to Save as PDF / Print</button>
        </div>
        <div class="header">
            <h1>COLLEGE ERP MANAGEMENT SYSTEM</h1>
            <h3>Official Student Evaluation Report (Marksheet)</h3>
        </div>
        <table class="meta-table">
            <tr>
                <td class="meta-label">Class / Section:</td>
                <td class="meta-value">{{ class_name }}</td>
                <td class="meta-label">Date Generated:</td>
                <td class="meta-value" id="currentDate"></td>
            </tr>
            <tr>
                <td class="meta-label">Subject:</td>
                <td class="meta-value">{{ subject }}</td>
                <td class="meta-label">Issued By:</td>
                <td class="meta-value">{{ faculty_name }}</td>
            </tr>
        </table>
        <table class="marks-table">
            <thead>
                <tr>
                    <th class="text-start" rowspan="2" style="width: 5%;">Sr. No.</th>
                    <th class="text-start" rowspan="2" style="width: 25%;">Student Name</th>
                    <th class="text-start" rowspan="2" style="width: 30%;">Email Address</th>
                    <th colspan="2">Theory (60:40)</th>
                    <th colspan="2">Practical (60:40)</th>
                    <th rowspan="2" style="width: 10%; background-color: #e2e8f0;">Grand Total<br>(Max 200)</th>
                </tr>
                <tr>
                    <th style="width: 7.5%;">CIE (60)</th>
                    <th style="width: 7.5%;">ESE (40)</th>
                    <th style="width: 7.5%;">CIE (60)</th>
                    <th style="width: 7.5%;">ESE (40)</th>
                </tr>
            </thead>
            <tbody>
                {% for row in report_data %}
                <tr>
                    <td class="text-start">{{ loop.index }}</td>
                    <td class="text-start" style="font-weight: bold; color: #1e293b;">{{ row.name }}</td>
                    <td class="text-start" style="color: #64748b;">{{ row.email }}</td>
                    <td>{{ row.cie_t }}</td>
                    <td>{{ row.ese_t }}</td>
                    <td>{{ row.cie_p }}</td>
                    <td>{{ row.ese_p }}</td>
                    <td style="font-weight: bold; color: #16a34a; background-color: #f8fafc;">{{ row.total }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        <div style="margin-top: 50px; text-align: right;">
            <div style="display: inline-block; text-align: center;">
                <div class="sign-box">Faculty Signature<br>({{ faculty_name }})</div>
            </div>
        </div>
        <script>
            const d = new Date();
            document.getElementById('currentDate').innerText = d.toLocaleDateString('en-IN', {day: 'numeric', month: 'short', year: 'numeric'});
        </script>
    </body>
    </html>
    """
    return render_template_string(pdf_template, class_name=class_name, subject=subject, faculty_name=faculty_name, report_data=report_data)

@app.route('/student_dashboard')
def student_dashboard():
    if 'role' not in session or session['role'] != 'student':
        return redirect(url_for('login', role='student'))
        
    student_email = session['user']
    
    conn = sqlite3.connect('college_erp_final.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM students WHERE email=?", (student_email,))
    student_data = cursor.fetchone()
    student_name = student_data[0] if student_data else "Student"
    
    subjects_list = ["Python Programming", "Database Management (DBMS)", "Web Technology", "Data Structures (DSA)", "Mathematics", "Computer Networks"]
    
    attendance_report = []
    total_lectures_all = 0
    total_present_all = 0
    
    for sub in subjects_list:
        cursor.execute("SELECT faculty_name FROM attendance WHERE email=? AND subject=? AND faculty_name IS NOT NULL ORDER BY id DESC LIMIT 1", (student_email, sub))
        fac_row = cursor.fetchone()
        assigned_faculty = fac_row[0] if fac_row else "Not Marked Yet"
        
        cursor.execute("SELECT COUNT(*) FROM attendance WHERE email=? AND subject=?", (student_email, sub))
        total_lectures = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM attendance WHERE email=? AND subject=? AND status='Present'", (student_email, sub))
        total_present = cursor.fetchone()[0]
        
        percentage = round((total_present / total_lectures * 100), 2) if total_lectures > 0 else 0
        
        total_lectures_all += total_lectures
        total_present_all += total_present
        
        attendance_report.append({
            "subject": sub,
            "faculty": assigned_faculty,
            "total": total_lectures,
            "present": total_present,
            "absent": total_lectures - total_present,
            "percentage": percentage
        })
        
    overall_attendance_pct = round((total_present_all / total_lectures_all * 100), 2) if total_lectures_all > 0 else 0
    
    marks_report = []
    total_grade_points = 0
    counted_subjects = 0
    
    for sub in subjects_list:
        cursor.execute("SELECT cie_theory, cie_practical FROM marks WHERE email=? AND subject=?", (student_email, sub))
        row = cursor.fetchone()
        cie_t, cie_p = row if row else (0, 0)
        total_cie = cie_t + cie_p
        
        pct = (total_cie / 120) * 100 if total_cie > 0 else 0
        if pct >= 85: gp = 10
        elif pct >= 75: gp = 9
        elif pct >= 65: gp = 8
        elif pct >= 55: gp = 7
        elif pct >= 45: gp = 6
        elif pct >= 35: gp = 5
        else: gp = 0
        
        total_grade_points += gp
        counted_subjects += 1
        
        marks_report.append({
            "subject": sub,
            "cie_theory": cie_t,
            "cie_practical": cie_p,
            "total_cie": total_cie,
            "grade_point": gp
        })
        
    auto_cgpa = round((total_grade_points / counted_subjects), 2) if counted_subjects > 0 else 0.00
    conn.close()
    
    return render_template('student_dashboard.html', 
                           student_name=student_name,
                           student_email=student_email,
                           attendance_report=attendance_report,
                           overall_attendance=overall_attendance_pct,
                           marks_report=marks_report,
                           auto_cgpa=auto_cgpa)

@app.route('/download-admit-card')
def download_admit_card():
    if 'role' not in session or session['role'] != 'student':
        return redirect(url_for('login', role='student'))
    
    student_email = session['user']
    conn = sqlite3.connect('college_erp_final.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM students WHERE email=?", (student_email,))
    student = cursor.fetchone()
    
    subjects_list = ["Python Programming", "Database Management (DBMS)", "Web Technology", "Data Structures (DSA)", "Mathematics", "Computer Networks"]
    
    eligible_subjects = []
    
    for sub in subjects_list:
        cursor.execute("SELECT COUNT(*) FROM attendance WHERE email=? AND subject=?", (student_email, sub))
        total_lec = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM attendance WHERE email=? AND subject=? AND status='Present'", (student_email, sub))
        present_lec = cursor.fetchone()[0]
        
        sub_percentage = (present_lec / total_lec * 100) if total_lec > 0 else 100.0
        
        if sub_percentage >= 60.0:
            eligible_subjects.append(sub)
            
    conn.close()
    
    student_dict = {
        "name": student[1] if student else "Student",
        "email": student[2] if student else student_email,
        "class_name": student[3] if student else "N/A"
    }
    
    return render_template('admit_card.html', 
                           student=student_dict, 
                           eligible_subjects=eligible_subjects)

@app.route('/delete_student/<int:id>', methods=['POST'])
def delete_student(id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login', role='student'))
        
    conn = sqlite3.connect('college_erp_final.db')
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM students WHERE id=?", (id,))
    student = cursor.fetchone()
    if student:
        email = student[0]
        cursor.execute("DELETE FROM users WHERE username=? AND role='student'", (email,))
        cursor.execute("DELETE FROM attendance WHERE email=?", (email,))
        cursor.execute("DELETE FROM marks WHERE email=?", (email,))
        cursor.execute("DELETE FROM students WHERE id=?", (id,))
        conn.commit()
        flash("Student deleted successfully.", "success")
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/delete_all_students', methods=['POST'])
def delete_all_students():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login', role='student'))
        
    conn = sqlite3.connect('college_erp_final.db')
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE role='student'")
        cursor.execute("DELETE FROM students")
        cursor.execute("DELETE FROM attendance")
        cursor.execute("DELETE FROM marks")
        conn.commit()
        flash("All students and relevant records deleted successfully.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {str(e)}", "danger")
    finally:
        conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/delete_faculty/<int:id>', methods=['POST'])
def delete_faculty(id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login', role='student'))
        
    conn = sqlite3.connect('college_erp_final.db')
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM faculty WHERE id=?", (id,))
    fac = cursor.fetchone()
    if fac:
        email = fac[0]
        cursor.execute("DELETE FROM users WHERE username=? AND role='faculty'", (email,))
        cursor.execute("DELETE FROM faculty WHERE id=?", (id,))
        conn.commit()
        flash("Faculty deleted successfully.", "success")
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login', role='student'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        new_password = request.form.get('new_password')
        role = request.form.get('role')
        
        conn = sqlite3.connect('college_erp_final.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=? AND role=?", (email, role))
        user = cursor.fetchone()
        
        if user:
            cursor.execute("UPDATE users SET password=? WHERE username=? AND role=?", (new_password, email, role))
            conn.commit()
            flash("Password updated successfully! Please login.", "success")
            conn.close()
            return redirect(url_for('login', role=role))
        else:
            flash("User not found with this email and role.", "danger")
            conn.close()
            
    return render_template('forgot_password.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)