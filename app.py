from flask import Flask, render_template, request, redirect, url_for, jsonify, g
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / 'lms.db'

app = Flask(__name__)
app.config['DATABASE'] = str(DB_PATH)


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
        db.row_factory = sqlite3.Row
    return db


def init_db():
    db = sqlite3.connect(app.config['DATABASE'])
    cur = db.cursor()
    cur.executescript('''
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT
    );

    CREATE TABLE IF NOT EXISTS enrollments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        course_id INTEGER NOT NULL,
        FOREIGN KEY(student_id) REFERENCES students(id),
        FOREIGN KEY(course_id) REFERENCES courses(id)
    );
    ''')
    db.commit()
    db.close()


def seed_courses():
    """Insert a few sample courses if the courses table is empty."""
    conn = sqlite3.connect(app.config['DATABASE'])
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM courses')
    count = cur.fetchone()[0]
    if count == 0:
        samples = [
            ('Math', 'Fundamentals of mathematics.'),
            ('Science', 'Introduction to basic sciences.'),
            ('History', 'World history overview.'),
            ('Programming', 'Intro to programming with Python.')
        ]
        cur.executemany('INSERT INTO courses (title, description) VALUES (?, ?)', samples)
        conn.commit()
    conn.close()


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.route('/')
def index():
    db = get_db()
    courses = db.execute('SELECT * FROM courses').fetchall()
    return render_template('index.html', courses=courses)


@app.route('/courses/<int:course_id>')
def course_detail(course_id):
    db = get_db()
    course = db.execute('SELECT * FROM courses WHERE id=?', (course_id,)).fetchone()
    students = db.execute('''
        SELECT s.* FROM students s
        JOIN enrollments e ON e.student_id = s.id
        WHERE e.course_id = ?
    ''', (course_id,)).fetchall()
    return render_template('course.html', course=course, students=students)


@app.route('/create_course', methods=['GET', 'POST'])
def create_course():
    if request.method == 'POST':
        title = request.form['title']
        desc = request.form.get('description', '')
        db = get_db()
        db.execute('INSERT INTO courses (title, description) VALUES (?, ?)', (title, desc))
        db.commit()
        return redirect(url_for('index'))
    return render_template('create_course.html')


@app.route('/enroll', methods=['POST'])
def enroll():
    student_name = request.form['name']
    student_email = request.form.get('email', '')
    course_id = int(request.form['course_id'])
    db = get_db()
    # find or create student
    student = db.execute('SELECT * FROM students WHERE email = ? AND name = ?', (student_email, student_name)).fetchone()
    if not student:
        cur = db.execute('INSERT INTO students (name, email) VALUES (?, ?)', (student_name, student_email))
        student_id = cur.lastrowid
    else:
        student_id = student['id']
    # add enrollment if not exists
    exists = db.execute('SELECT * FROM enrollments WHERE student_id = ? AND course_id = ?', (student_id, course_id)).fetchone()
    if not exists:
        db.execute('INSERT INTO enrollments (student_id, course_id) VALUES (?, ?)', (student_id, course_id))
        db.commit()
    return redirect(url_for('course_detail', course_id=course_id))


@app.route('/select_course', methods=['POST'])
def select_course():
    """Redirect to the selected course's detail page from a simple form on the homepage."""
    course_id = request.form.get('course_id')
    if not course_id:
        return redirect(url_for('index'))
    try:
        cid = int(course_id)
    except ValueError:
        return redirect(url_for('index'))
    return redirect(url_for('course_detail', course_id=cid))


@app.route('/seed')
def seed_route():
    """HTTP endpoint to seed sample courses (safe to call multiple times)."""
    seed_courses()
    return redirect(url_for('index'))


### Simple JSON API


@app.route('/api/courses', methods=['GET', 'POST'])
def api_courses():
    db = get_db()
    if request.method == 'GET':
        courses = db.execute('SELECT * FROM courses').fetchall()
        return jsonify([dict(c) for c in courses])
    data = request.get_json() or {}
    title = data.get('title')
    description = data.get('description', '')
    if not title:
        return jsonify({'error': 'title required'}), 400
    cur = db.execute('INSERT INTO courses (title, description) VALUES (?, ?)', (title, description))
    db.commit()
    course_id = cur.lastrowid
    course = db.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    return jsonify(dict(course)), 201


@app.route('/api/courses/<int:course_id>/students', methods=['GET'])
def api_course_students(course_id):
    db = get_db()
    students = db.execute('''
        SELECT s.* FROM students s
        JOIN enrollments e ON e.student_id = s.id
        WHERE e.course_id = ?
    ''', (course_id,)).fetchall()
    return jsonify([dict(s) for s in students])


if __name__ == '__main__':
    if not DB_PATH.exists():
        init_db()
    # ensure we have some starter courses for users to choose from
    seed_courses()
    app.run(debug=True)
