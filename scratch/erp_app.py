# ============================================================
#  COLLEGE ERP SYSTEM — Flask Backend
#  File: app.py
#  Run: python app.py
# ============================================================

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import mysql.connector
import os

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# ─────────────────────────────────────────
#  DB CONFIG  ← Update these values with your AWS RDS details
# ─────────────────────────────────────────
DB_CONFIG = {
    'host':     ' ',
    'user':     ' ',
    'password': ' ',
    'database': ' ',
    'port':     ****,
    'autocommit': True/False
}

def get_db():
    """Return a fresh MySQL connection."""
    return mysql.connector.connect(**DB_CONFIG)

def query(sql, params=(), fetch='all'):
    """Helper: run a query and return results."""
    conn = get_db()
    cur  = conn.cursor(dictionary=True)
    cur.execute(sql, params)
    if fetch == 'all':
        result = cur.fetchall()
    elif fetch == 'one':
        result = cur.fetchone()
    else:
        result = cur.lastrowid
    cur.close()
    conn.close()
    return result

def mutate(sql, params=()):
    """Helper: run INSERT / UPDATE / DELETE, return lastrowid."""
    conn = get_db()
    cur  = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    lid = cur.lastrowid
    cur.close()
    conn.close()
    return lid

# ══════════════════════════════════════════
#  SERVE FRONTEND
# ══════════════════════════════════════════
@app.route('/')
def index():
    return render_template('index.html')

# ══════════════════════════════════════════
#  DASHBOARD STATS
# ══════════════════════════════════════════
@app.route('/api/dashboard')
def dashboard():
    stats = {
        'total_students': query("SELECT COUNT(*) AS c FROM students WHERE status='active'", fetch='one')['c'],
        'total_faculty':  query("SELECT COUNT(*) AS c FROM faculty  WHERE status='active'", fetch='one')['c'],
        'total_subjects': query("SELECT COUNT(*) AS c FROM subjects",                       fetch='one')['c'],
        'total_depts':    query("SELECT COUNT(*) AS c FROM departments",                    fetch='one')['c'],
        'fees_collected': query("SELECT COALESCE(SUM(paid),0) AS s FROM fees",              fetch='one')['s'],
        'fees_pending':   query("SELECT COALESCE(SUM(amount-paid),0) AS s FROM fees WHERE status!='paid'", fetch='one')['s'],
        'dept_wise': query("""
            SELECT d.name, COUNT(s.id) AS total
            FROM departments d LEFT JOIN students s ON s.dept_id=d.id
            GROUP BY d.id, d.name
        """),
        'attendance_summary': query("""
            SELECT status, COUNT(*) AS cnt FROM attendance GROUP BY status
        """),
    }
    # Convert Decimal to float for JSON
    stats['fees_collected'] = float(stats['fees_collected'])
    stats['fees_pending']   = float(stats['fees_pending'])
    return jsonify(stats)

# ══════════════════════════════════════════
#  DEPARTMENTS
# ══════════════════════════════════════════
@app.route('/api/departments', methods=['GET'])
def get_departments():
    return jsonify(query("SELECT * FROM departments ORDER BY name"))

@app.route('/api/departments', methods=['POST'])
def add_department():
    d = request.json
    lid = mutate(
        "INSERT INTO departments (name, code, hod) VALUES (%s,%s,%s)",
        (d['name'], d['code'], d.get('hod',''))
    )
    return jsonify({'success': True, 'id': lid}), 201

@app.route('/api/departments/<int:dept_id>', methods=['PUT'])
def update_department(dept_id):
    d = request.json
    mutate("UPDATE departments SET name=%s, code=%s, hod=%s WHERE id=%s",
           (d['name'], d['code'], d.get('hod',''), dept_id))
    return jsonify({'success': True})

@app.route('/api/departments/<int:dept_id>', methods=['DELETE'])
def delete_department(dept_id):
    mutate("DELETE FROM departments WHERE id=%s", (dept_id,))
    return jsonify({'success': True})

# ══════════════════════════════════════════
#  STUDENTS
# ══════════════════════════════════════════
@app.route('/api/students', methods=['GET'])
def get_students():
    dept_id = request.args.get('dept_id')
    sem     = request.args.get('semester')
    sql = """
        SELECT s.*, d.name AS dept_name, d.code AS dept_code
        FROM students s LEFT JOIN departments d ON s.dept_id=d.id
        WHERE s.status='active'
    """
    params = []
    if dept_id: sql += " AND s.dept_id=%s"; params.append(dept_id)
    if sem:     sql += " AND s.semester=%s"; params.append(sem)
    sql += " ORDER BY s.roll_no"
    return jsonify(query(sql, params))

@app.route('/api/students/<int:sid>', methods=['GET'])
def get_student(sid):
    s = query("""
        SELECT s.*, d.name AS dept_name FROM students s
        LEFT JOIN departments d ON s.dept_id=d.id WHERE s.id=%s
    """, (sid,), fetch='one')
    if not s: return jsonify({'error': 'Not found'}), 404
    s['marks']      = query("""
        SELECT m.*, sub.name AS subject_name, sub.code AS subject_code
        FROM marks m JOIN subjects sub ON m.subject_id=sub.id
        WHERE m.student_id=%s
    """, (sid,))
    s['attendance'] = query("""
        SELECT a.*, sub.name AS subject_name
        FROM attendance a JOIN subjects sub ON a.subject_id=sub.id
        WHERE a.student_id=%s ORDER BY a.date DESC LIMIT 20
    """, (sid,))
    s['fees'] = query("SELECT * FROM fees WHERE student_id=%s", (sid,))
    for f in s['fees']:
        f['amount'] = float(f['amount'])
        f['paid']   = float(f['paid'])
        f['due_date']  = str(f['due_date'])  if f['due_date']  else None
        f['paid_date'] = str(f['paid_date']) if f['paid_date'] else None
    return jsonify(s)

@app.route('/api/students', methods=['POST'])
def add_student():
    d = request.json
    lid = mutate("""
        INSERT INTO students (roll_no, name, email, phone, dept_id, semester, dob, address)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, (d['roll_no'], d['name'], d['email'], d.get('phone'),
          d.get('dept_id'), d.get('semester'), d.get('dob'), d.get('address')))
    return jsonify({'success': True, 'id': lid}), 201

@app.route('/api/students/<int:sid>', methods=['PUT'])
def update_student(sid):
    d = request.json
    mutate("""
        UPDATE students SET name=%s, email=%s, phone=%s,
        dept_id=%s, semester=%s, dob=%s, address=%s WHERE id=%s
    """, (d['name'], d['email'], d.get('phone'), d.get('dept_id'),
          d.get('semester'), d.get('dob'), d.get('address'), sid))
    return jsonify({'success': True})

@app.route('/api/students/<int:sid>', methods=['DELETE'])
def delete_student(sid):
    mutate("UPDATE students SET status='inactive' WHERE id=%s", (sid,))
    return jsonify({'success': True})

# ══════════════════════════════════════════
#  FACULTY
# ══════════════════════════════════════════
@app.route('/api/faculty', methods=['GET'])
def get_faculty():
    return jsonify(query("""
        SELECT f.*, d.name AS dept_name FROM faculty f
        LEFT JOIN departments d ON f.dept_id=d.id
        WHERE f.status='active' ORDER BY f.name
    """))

@app.route('/api/faculty', methods=['POST'])
def add_faculty():
    d = request.json
    lid = mutate("""
        INSERT INTO faculty (emp_id, name, email, phone, dept_id, designation, qualification)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (d['emp_id'], d['name'], d['email'], d.get('phone'),
          d.get('dept_id'), d.get('designation'), d.get('qualification')))
    return jsonify({'success': True, 'id': lid}), 201

@app.route('/api/faculty/<int:fid>', methods=['PUT'])
def update_faculty(fid):
    d = request.json
    mutate("""
        UPDATE faculty SET name=%s, email=%s, phone=%s,
        dept_id=%s, designation=%s, qualification=%s WHERE id=%s
    """, (d['name'], d['email'], d.get('phone'), d.get('dept_id'),
          d.get('designation'), d.get('qualification'), fid))
    return jsonify({'success': True})

@app.route('/api/faculty/<int:fid>', methods=['DELETE'])
def delete_faculty(fid):
    mutate("UPDATE faculty SET status='inactive' WHERE id=%s", (fid,))
    return jsonify({'success': True})

# ══════════════════════════════════════════
#  SUBJECTS
# ══════════════════════════════════════════
@app.route('/api/subjects', methods=['GET'])
def get_subjects():
    return jsonify(query("""
        SELECT sub.*, d.name AS dept_name, f.name AS faculty_name
        FROM subjects sub
        LEFT JOIN departments d ON sub.dept_id=d.id
        LEFT JOIN faculty     f ON sub.faculty_id=f.id
        ORDER BY sub.code
    """))

@app.route('/api/subjects', methods=['POST'])
def add_subject():
    d = request.json
    lid = mutate("""
        INSERT INTO subjects (code, name, dept_id, semester, credits, faculty_id)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (d['code'], d['name'], d.get('dept_id'), d.get('semester'),
          d.get('credits', 3), d.get('faculty_id')))
    return jsonify({'success': True, 'id': lid}), 201

@app.route('/api/subjects/<int:sub_id>', methods=['DELETE'])
def delete_subject(sub_id):
    mutate("DELETE FROM subjects WHERE id=%s", (sub_id,))
    return jsonify({'success': True})

# ══════════════════════════════════════════
#  ATTENDANCE
# ══════════════════════════════════════════
@app.route('/api/attendance', methods=['GET'])
def get_attendance():
    student_id = request.args.get('student_id')
    subject_id = request.args.get('subject_id')
    sql = """
        SELECT a.*, s.name AS student_name, s.roll_no,
               sub.name AS subject_name, sub.code AS subject_code
        FROM attendance a
        JOIN students s  ON a.student_id=s.id
        JOIN subjects sub ON a.subject_id=sub.id WHERE 1=1
    """
    params = []
    if student_id: sql += " AND a.student_id=%s"; params.append(student_id)
    if subject_id: sql += " AND a.subject_id=%s"; params.append(subject_id)
    sql += " ORDER BY a.date DESC LIMIT 100"
    rows = query(sql, params)
    for r in rows:
        r['date'] = str(r['date'])
    return jsonify(rows)

@app.route('/api/attendance', methods=['POST'])
def add_attendance():
    d = request.json
    mutate("""
        INSERT INTO attendance (student_id, subject_id, date, status)
        VALUES (%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE status=%s
    """, (d['student_id'], d['subject_id'], d['date'], d['status'], d['status']))
    return jsonify({'success': True}), 201

# ══════════════════════════════════════════
#  MARKS
# ══════════════════════════════════════════
@app.route('/api/marks', methods=['GET'])
def get_marks():
    student_id = request.args.get('student_id')
    sql = """
        SELECT m.*, s.name AS student_name, s.roll_no,
               sub.name AS subject_name, sub.code
        FROM marks m
        JOIN students s   ON m.student_id=s.id
        JOIN subjects sub ON m.subject_id=sub.id WHERE 1=1
    """
    params = []
    if student_id: sql += " AND m.student_id=%s"; params.append(student_id)
    rows = query(sql, params)
    for r in rows:
        r['marks']     = float(r['marks'])     if r['marks']     else None
        r['max_marks'] = float(r['max_marks']) if r['max_marks'] else None
    return jsonify(rows)

@app.route('/api/marks', methods=['POST'])
def add_marks():
    d = request.json
    mutate("""
        INSERT INTO marks (student_id, subject_id, exam_type, marks, max_marks, grade)
        VALUES (%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE marks=%s, grade=%s
    """, (d['student_id'], d['subject_id'], d['exam_type'],
          d['marks'], d.get('max_marks', 100), d.get('grade',''),
          d['marks'], d.get('grade','')))
    return jsonify({'success': True}), 201

# ══════════════════════════════════════════
#  FEES
# ══════════════════════════════════════════
@app.route('/api/fees', methods=['GET'])
def get_fees():
    rows = query("""
        SELECT f.*, s.name AS student_name, s.roll_no, d.name AS dept_name
        FROM fees f JOIN students s ON f.student_id=s.id
        LEFT JOIN departments d ON s.dept_id=d.id
        ORDER BY f.status, f.due_date
    """)
    for r in rows:
        r['amount']    = float(r['amount'])
        r['paid']      = float(r['paid'])
        r['due_date']  = str(r['due_date'])  if r['due_date']  else None
        r['paid_date'] = str(r['paid_date']) if r['paid_date'] else None
    return jsonify(rows)

@app.route('/api/fees/<int:fee_id>/pay', methods=['PUT'])
def pay_fee(fee_id):
    d = request.json
    pay_amount = float(d.get('amount', 0))
    fee = query("SELECT * FROM fees WHERE id=%s", (fee_id,), fetch='one')
    if not fee: return jsonify({'error': 'Not found'}), 404
    new_paid = float(fee['paid']) + pay_amount
    total    = float(fee['amount'])
    status   = 'paid' if new_paid >= total else 'partial'
    from datetime import date
    mutate("UPDATE fees SET paid=%s, status=%s, paid_date=%s WHERE id=%s",
           (new_paid, status, str(date.today()), fee_id))
    return jsonify({'success': True, 'new_paid': new_paid, 'status': status})

# ══════════════════════════════════════════
if __name__ == '__main__':

    app.run(host='0.0.0.0', port=5000, debug=True)
