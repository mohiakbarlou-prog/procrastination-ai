import sqlite3
from datetime import date, datetime, timedelta

import jdatetime

from config import DB_PATH


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_column(cursor, table_name, column_name, definition):
    columns = {
        row[1]
        for row in cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name not in columns:
        cursor.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"
        )


# ================================================================
# Date helpers
# ================================================================

def jalali_from_gregorian(value):
    if value is None:
        return ""
    if isinstance(value, datetime):
        value = value.date()
    if not isinstance(value, date):
        value = date.fromisoformat(str(value)[:10])
    return jdatetime.date.fromgregorian(date=value).strftime("%Y/%m/%d")


def jalali_to_gregorian(year, month, day):
    return jdatetime.date(int(year), int(month), int(day)).togregorian()


def to_persian_digits(value):
    if value is None:
        return ""
    return str(value).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


# ================================================================
# Database initialization + migration
# ================================================================

def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_code TEXT UNIQUE,
            age INTEGER,
            gender TEXT,
            degree TEXT,
            semester INTEGER,
            use_level TEXT,
            university TEXT,
            major TEXT,
            registered_at_jalali TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_code TEXT,
            assessment_type TEXT,
            total_score REAL,
            level TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interventions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_code TEXT,
            profile TEXT,
            intervention_name TEXT,
            intervention_description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_code TEXT,
            task_name TEXT,
            planned_minutes INTEGER,
            actual_minutes INTEGER,
            completed INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS study_participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_code TEXT UNIQUE,
            group_type TEXT NOT NULL,
            start_date TEXT,
            end_date TEXT,
            status TEXT DEFAULT 'active',
            consent INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assessment_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assessment_id INTEGER UNIQUE,
            q1 INTEGER, q2 INTEGER, q3 INTEGER, q4 INTEGER,
            q5 INTEGER, q6 INTEGER, q7 INTEGER, q8 INTEGER,
            q9 INTEGER, q10 INTEGER, q11 INTEGER, q12 INTEGER,
            q13 INTEGER, q14 INTEGER, q15 INTEGER, q16 INTEGER,
            q17 INTEGER, q18 INTEGER, q19 INTEGER, q20 INTEGER,
            q21 INTEGER, q22 INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (assessment_id) REFERENCES assessments(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS study_interventions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_code TEXT,
            day_number INTEGER,
            intervention_order INTEGER DEFAULT 1,
            profile TEXT,
            profile_score REAL,
            profile_level TEXT,
            overall_level TEXT,
            estimated_level TEXT,
            intervention_name TEXT,
            intervention_description TEXT,
            intensity TEXT,
            shown_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_code, day_number, intervention_order)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_code TEXT,
            day_number INTEGER,
            action_status TEXT,
            actual_minutes INTEGER,
            coach_used INTEGER DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            checkin_question TEXT,
            checkin_answer TEXT,
            UNIQUE(student_code, day_number)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS coach_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_code TEXT,
            day_number INTEGER,
            student_message TEXT,
            coach_response TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Existing databases created with older versions need these columns.
    _ensure_column(cursor, "students", "registered_at_jalali", "TEXT")
    _ensure_column(cursor, "daily_logs", "checkin_question", "TEXT")
    _ensure_column(cursor, "daily_logs", "checkin_answer", "TEXT")

    conn.commit()
    conn.close()


# ================================================================
# Students
# ================================================================

def save_student(student_data):
    registered = jalali_from_gregorian(date.today())
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO students (
                student_code, age, gender, degree, semester,
                use_level, university, major, registered_at_jalali
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(student_code) DO UPDATE SET
                age = excluded.age,
                gender = excluded.gender,
                degree = excluded.degree,
                semester = excluded.semester,
                use_level = excluded.use_level,
                university = excluded.university,
                major = excluded.major,
                registered_at_jalali = COALESCE(
                    students.registered_at_jalali,
                    excluded.registered_at_jalali
                )
        """, (
            student_data["student_code"],
            int(student_data["age"]),
            student_data["gender"],
            student_data["degree"],
            int(student_data["semester"]),
            student_data["daily_use"],
            student_data["university"],
            student_data["major"],
            registered,
        ))
        conn.commit()
    finally:
        conn.close()


def load_student(student_code):
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT student_code, age, gender, degree, semester,
                   use_level, university, major, registered_at_jalali
            FROM students
            WHERE student_code = ?
        """, (student_code,)).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    return {
        "student_code": row[0],
        "age": row[1],
        "gender": row[2],
        "degree": row[3],
        "semester": row[4],
        "daily_use": row[5],
        "university": row[6],
        "major": row[7],
        "registered_at_jalali": row[8],
    }


# ================================================================
# Assessments
# ================================================================

def save_assessment(student_code, assessment_type, total_score, level):
    conn = get_connection()
    try:
        cur = conn.execute("""
            INSERT INTO assessments (
                student_code, assessment_type, total_score, level
            ) VALUES (?, ?, ?, ?)
        """, (student_code, assessment_type, total_score, level))
        assessment_id = cur.lastrowid
        conn.commit()
        return assessment_id
    finally:
        conn.close()


def get_assessment(student_code, assessment_type):
    conn = get_connection()
    try:
        return conn.execute("""
            SELECT id, student_code, assessment_type,
                   total_score, level, created_at
            FROM assessments
            WHERE student_code = ? AND assessment_type = ?
            ORDER BY id DESC
            LIMIT 1
        """, (student_code, assessment_type)).fetchone()
    finally:
        conn.close()


def has_assessment(student_code, assessment_type):
    return get_assessment(student_code, assessment_type) is not None


def _normalize_answers(answers):
    if isinstance(answers, dict):
        values = [answers.get(f"q{i}") for i in range(1, 23)]
    else:
        values = list(answers)
    if len(values) != 22:
        raise ValueError("answers must contain exactly 22 questionnaire responses")
    if any(value is None for value in values):
        raise ValueError("answers must contain values for q1 through q22")
    return [int(value) for value in values]


def save_assessment_responses(assessment_id, answers):
    values = _normalize_answers(answers)
    conn = get_connection()
    try:
        conn.execute("""
            INSERT OR REPLACE INTO assessment_responses (
                assessment_id,
                q1,q2,q3,q4,q5,q6,q7,q8,q9,q10,q11,
                q12,q13,q14,q15,q16,q17,q18,q19,q20,q21,q22
            ) VALUES (
                ?,?,?,?,?,?,?,?,?,?,?,?,
                ?,?,?,?,?,?,?,?,?,?,?
            )
        """, (assessment_id, *values))
        conn.commit()
    finally:
        conn.close()


def save_assessment_with_responses(
    student_code, assessment_type, total_score, level, answers
):
    values = _normalize_answers(answers)
    conn = get_connection()
    try:
        cur = conn.execute("""
            INSERT INTO assessments (
                student_code, assessment_type, total_score, level
            ) VALUES (?, ?, ?, ?)
        """, (student_code, assessment_type, total_score, level))
        assessment_id = cur.lastrowid

        conn.execute("""
            INSERT INTO assessment_responses (
                assessment_id,
                q1,q2,q3,q4,q5,q6,q7,q8,q9,q10,q11,
                q12,q13,q14,q15,q16,q17,q18,q19,q20,q21,q22
            ) VALUES (
                ?,?,?,?,?,?,?,?,?,?,?,?,
                ?,?,?,?,?,?,?,?,?,?,?
            )
        """, (assessment_id, *values))
        conn.commit()
        return assessment_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_assessment_responses(assessment_id):
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT
                q1,q2,q3,q4,q5,q6,q7,q8,q9,q10,q11,
                q12,q13,q14,q15,q16,q17,q18,q19,q20,q21,q22
            FROM assessment_responses
            WHERE assessment_id = ?
        """, (assessment_id,)).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    return {f"q{i}": row[i - 1] for i in range(1, 23)}


# ================================================================
# Interventions
# ================================================================

def save_intervention(student_code, profile, intervention_name, intervention_description):
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO interventions (
                student_code, profile, intervention_name,
                intervention_description
            ) VALUES (?, ?, ?, ?)
        """, (
            student_code, profile, intervention_name, intervention_description
        ))
        conn.commit()
    finally:
        conn.close()


def save_study_intervention(
    student_code,
    day_number,
    profile,
    profile_score,
    profile_level,
    overall_level,
    estimated_level,
    intervention_name,
    intervention_description,
    intensity,
    intervention_order=1,
):
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO study_interventions (
                student_code, day_number, intervention_order,
                profile, profile_score, profile_level,
                overall_level, estimated_level,
                intervention_name, intervention_description, intensity
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(student_code, day_number, intervention_order)
            DO UPDATE SET
                profile = excluded.profile,
                profile_score = excluded.profile_score,
                profile_level = excluded.profile_level,
                overall_level = excluded.overall_level,
                estimated_level = excluded.estimated_level,
                intervention_name = excluded.intervention_name,
                intervention_description = excluded.intervention_description,
                intensity = excluded.intensity,
                shown_at = CURRENT_TIMESTAMP
        """, (
            student_code, int(day_number), int(intervention_order),
            profile, profile_score, profile_level,
            overall_level, estimated_level,
            intervention_name, intervention_description, intensity,
        ))
        conn.commit()
    finally:
        conn.close()


def get_study_interventions(student_code, day_number=None):
    conn = get_connection()
    try:
        query = """
            SELECT
                id, student_code, day_number, intervention_order,
                profile, profile_score, profile_level,
                overall_level, estimated_level,
                intervention_name, intervention_description,
                intensity, shown_at
            FROM study_interventions
            WHERE student_code = ?
        """
        params = [student_code]
        if day_number is None:
            query += " ORDER BY day_number, intervention_order"
        else:
            query += " AND day_number = ? ORDER BY intervention_order"
            params.append(int(day_number))
        return conn.execute(query, params).fetchall()
    finally:
        conn.close()


# ================================================================
# Study participant + study date
# ================================================================

def register_study_participant(
    student_code,
    group_type,
    start_date=None,
    end_date=None,
    consent=True,
    status="active",
):
    if group_type not in {"intervention", "control"}:
        raise ValueError("group_type must be 'intervention' or 'control'")

    if start_date is None:
        start_date = date.today().isoformat()
    elif isinstance(start_date, (date, datetime)):
        start_date = start_date.strftime("%Y-%m-%d")

    if isinstance(end_date, (date, datetime)):
        end_date = end_date.strftime("%Y-%m-%d")

    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO study_participants (
                student_code, group_type, start_date,
                end_date, status, consent
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(student_code) DO UPDATE SET
                group_type = excluded.group_type,
                start_date = excluded.start_date,
                end_date = excluded.end_date,
                status = excluded.status,
                consent = excluded.consent
        """, (
            student_code, group_type, start_date, end_date,
            status, int(bool(consent)),
        ))
        conn.commit()
    finally:
        conn.close()


def get_study_participant(student_code):
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT id, student_code, group_type, start_date,
                   end_date, status, consent, created_at
            FROM study_participants
            WHERE student_code = ?
        """, (student_code,)).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    return {
        "id": row[0],
        "student_code": row[1],
        "group_type": row[2],
        "start_date": row[3],
        "end_date": row[4],
        "status": row[5],
        "consent": bool(row[6]),
        "created_at": row[7],
    }


def get_study_day(student_code, today=None):
    participant = get_study_participant(student_code)
    if participant is None or not participant.get("start_date"):
        return None

    if today is None:
        today = date.today()
    elif isinstance(today, str):
        today = date.fromisoformat(today)
    elif isinstance(today, datetime):
        today = today.date()

    start = date.fromisoformat(str(participant["start_date"])[:10])
    return (today - start).days + 1


def get_study_date(student_code, day_number):
    participant = get_study_participant(student_code)
    if participant is None or not participant.get("start_date"):
        return None

    try:
        start = date.fromisoformat(str(participant["start_date"])[:10])
        return start + timedelta(days=int(day_number) - 1)
    except (TypeError, ValueError):
        return None


def complete_study_participant(student_code):
    conn = get_connection()
    try:
        conn.execute("""
            UPDATE study_participants
            SET status = 'completed', end_date = DATE('now')
            WHERE student_code = ?
        """, (student_code,))
        conn.commit()
    finally:
        conn.close()


# ================================================================
# Daily log
# ================================================================

def save_daily_log(
    student_code,
    day_number,
    action_status,
    actual_minutes=None,
    coach_used=False,
    notes="",
    checkin_question="",
    checkin_answer="",
):
    allowed = {"not_started", "partial", "completed"}
    if action_status not in allowed:
        raise ValueError(
            "action_status must be one of: not_started, partial, completed"
        )

    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO daily_logs (
                student_code, day_number, action_status,
                actual_minutes, coach_used, notes,
                checkin_question, checkin_answer
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(student_code, day_number)
            DO UPDATE SET
                action_status = excluded.action_status,
                actual_minutes = excluded.actual_minutes,
                coach_used = excluded.coach_used,
                notes = excluded.notes,
                checkin_question = excluded.checkin_question,
                checkin_answer = excluded.checkin_answer,
                created_at = CURRENT_TIMESTAMP
        """, (
            student_code,
            int(day_number),
            action_status,
            actual_minutes,
            int(bool(coach_used)),
            notes,
            checkin_question,
            checkin_answer,
        ))
        conn.commit()
    finally:
        conn.close()


def get_daily_log(student_code, day_number):
    conn = get_connection()
    try:
        return conn.execute("""
            SELECT
                id, student_code, day_number, action_status,
                actual_minutes, coach_used, notes, created_at,
                checkin_question, checkin_answer
            FROM daily_logs
            WHERE student_code = ? AND day_number = ?
        """, (student_code, int(day_number))).fetchone()
    finally:
        conn.close()


# ================================================================
# AI coach log
# ================================================================

def save_coach_log(student_code, day_number, student_message, coach_response):
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO coach_logs (
                student_code, day_number,
                student_message, coach_response
            ) VALUES (?, ?, ?, ?)
        """, (
            student_code, int(day_number),
            student_message, coach_response,
        ))
        conn.commit()
    finally:
        conn.close()
