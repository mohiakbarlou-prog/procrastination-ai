import os
from datetime import date, datetime, timedelta

import psycopg2
import jdatetime


# ================================================================
# Connection
# ================================================================

def get_connection():
    """Return a PostgreSQL connection using DATABASE_URL.

    Priority:
      1) Streamlit Secrets["DATABASE_URL"]
      2) Environment variable DATABASE_URL
    Never hardcode credentials in source code.
    """
    db_url = ""

    # تلاش برای خواندن از Streamlit Secrets
    try:
        import streamlit as st
        db_url = str(st.secrets.get("DATABASE_URL", "")).strip()
    except Exception:
        pass

    # fallback به متغیر محیطی
    if not db_url:
        db_url = os.environ.get("DATABASE_URL", "").strip()

    if not db_url:
        raise RuntimeError(
            "DATABASE_URL تنظیم نشده است. "
            "آن را در Streamlit Secrets یا متغیر محیطی قرار بده."
        )

    return psycopg2.connect(db_url)


# ================================================================
# Researcher authentication
# ================================================================

def verify_researcher_code(code):
    if not code:
        return None

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT researcher_code, role
                FROM researchers
                WHERE researcher_code = %s
                """,
                (code,),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if row:
        return {"code": row[0], "role": row[1]}
    return None


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
# Schema migration helper
# ================================================================

def _ensure_column(cursor, table_name, column_name, definition):
    """Add a column if it does not exist (PostgreSQL version)."""
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
        """,
        (table_name, column_name),
    )
    if cursor.fetchone() is None:
        cursor.execute(
            f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {definition}'
        )


# ================================================================
# Database initialization
# ================================================================

def initialize_database():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS researchers (
                    id SERIAL PRIMARY KEY,
                    researcher_code TEXT UNIQUE NOT NULL,
                    role TEXT DEFAULT 'researcher',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id SERIAL PRIMARY KEY,
                    student_code TEXT UNIQUE NOT NULL,
                    age INTEGER,
                    gender TEXT,
                    degree TEXT,
                    semester INTEGER,
                    use_level TEXT,
                    university TEXT,
                    major TEXT,
                    registered_at_jalali TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS assessments (
                    id SERIAL PRIMARY KEY,
                    student_code TEXT,
                    assessment_type TEXT,
                    total_score DOUBLE PRECISION,
                    level TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS interventions (
                    id SERIAL PRIMARY KEY,
                    student_code TEXT,
                    profile TEXT,
                    intervention_name TEXT,
                    intervention_description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS activities (
                    id SERIAL PRIMARY KEY,
                    student_code TEXT,
                    task_name TEXT,
                    planned_minutes INTEGER,
                    actual_minutes INTEGER,
                    completed INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS study_participants (
                    id SERIAL PRIMARY KEY,
                    student_code TEXT UNIQUE,
                    group_type TEXT NOT NULL,
                    start_date TEXT,
                    end_date TEXT,
                    status TEXT DEFAULT 'active',
                    consent INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS assessment_responses (
                    id SERIAL PRIMARY KEY,
                    assessment_id INTEGER UNIQUE REFERENCES assessments(id) ON DELETE CASCADE,
                    q1 INTEGER, q2 INTEGER, q3 INTEGER, q4 INTEGER,
                    q5 INTEGER, q6 INTEGER, q7 INTEGER, q8 INTEGER,
                    q9 INTEGER, q10 INTEGER, q11 INTEGER, q12 INTEGER,
                    q13 INTEGER, q14 INTEGER, q15 INTEGER, q16 INTEGER,
                    q17 INTEGER, q18 INTEGER, q19 INTEGER, q20 INTEGER,
                    q21 INTEGER, q22 INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS study_interventions (
                    id SERIAL PRIMARY KEY,
                    student_code TEXT,
                    day_number INTEGER,
                    intervention_order INTEGER DEFAULT 1,
                    profile TEXT,
                    profile_score DOUBLE PRECISION,
                    profile_level TEXT,
                    overall_level TEXT,
                    estimated_level TEXT,
                    intervention_name TEXT,
                    intervention_description TEXT,
                    intensity TEXT,
                    shown_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (student_code, day_number, intervention_order)
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS daily_logs (
                    id SERIAL PRIMARY KEY,
                    student_code TEXT,
                    day_number INTEGER,
                    action_status TEXT,
                    actual_minutes INTEGER,
                    coach_used INTEGER DEFAULT 0,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    checkin_question TEXT,
                    checkin_answer TEXT,
                    UNIQUE (student_code, day_number)
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS coach_logs (
                    id SERIAL PRIMARY KEY,
                    student_code TEXT,
                    day_number INTEGER,
                    student_message TEXT,
                    coach_response TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # ستون‌های سازگاری برای دیتابیس‌های قدیمی‌تر
            _ensure_column(cur, "students", "registered_at_jalali", "TEXT")
            _ensure_column(cur, "daily_logs", "checkin_question", "TEXT")
            _ensure_column(cur, "daily_logs", "checkin_answer", "TEXT")

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ================================================================
# Students
# ================================================================

def save_student(student_data):
    registered = jalali_from_gregorian(date.today())
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO students (
                    student_code, age, gender, degree, semester,
                    use_level, university, major, registered_at_jalali
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (student_code) DO UPDATE SET
                    age = EXCLUDED.age,
                    gender = EXCLUDED.gender,
                    degree = EXCLUDED.degree,
                    semester = EXCLUDED.semester,
                    use_level = EXCLUDED.use_level,
                    university = EXCLUDED.university,
                    major = EXCLUDED.major,
                    registered_at_jalali = COALESCE(
                        students.registered_at_jalali,
                        EXCLUDED.registered_at_jalali
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
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def load_student(student_code):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT student_code, age, gender, degree, semester,
                       use_level, university, major, registered_at_jalali
                FROM students
                WHERE student_code = %s
            """, (student_code,))
            row = cur.fetchone()
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
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO assessments (
                    student_code, assessment_type, total_score, level
                ) VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (student_code, assessment_type, total_score, level))
            assessment_id = cur.fetchone()[0]
        conn.commit()
        return assessment_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_assessment(student_code, assessment_type):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, student_code, assessment_type,
                       total_score, level, created_at
                FROM assessments
                WHERE student_code = %s AND assessment_type = %s
                ORDER BY id DESC
                LIMIT 1
            """, (student_code, assessment_type))
            return cur.fetchone()
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
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO assessment_responses (
                    assessment_id,
                    q1,q2,q3,q4,q5,q6,q7,q8,q9,q10,q11,
                    q12,q13,q14,q15,q16,q17,q18,q19,q20,q21,q22
                ) VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                )
                ON CONFLICT (assessment_id) DO UPDATE SET
                    q1 = EXCLUDED.q1,   q2 = EXCLUDED.q2,   q3 = EXCLUDED.q3,
                    q4 = EXCLUDED.q4,   q5 = EXCLUDED.q5,   q6 = EXCLUDED.q6,
                    q7 = EXCLUDED.q7,   q8 = EXCLUDED.q8,   q9 = EXCLUDED.q9,
                    q10 = EXCLUDED.q10, q11 = EXCLUDED.q11, q12 = EXCLUDED.q12,
                    q13 = EXCLUDED.q13, q14 = EXCLUDED.q14, q15 = EXCLUDED.q15,
                    q16 = EXCLUDED.q16, q17 = EXCLUDED.q17, q18 = EXCLUDED.q18,
                    q19 = EXCLUDED.q19, q20 = EXCLUDED.q20, q21 = EXCLUDED.q21,
                    q22 = EXCLUDED.q22
            """, (assessment_id, *values))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def save_assessment_with_responses(
    student_code, assessment_type, total_score, level, answers
):
    values = _normalize_answers(answers)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO assessments (
                    student_code, assessment_type, total_score, level
                ) VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (student_code, assessment_type, total_score, level))
            assessment_id = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO assessment_responses (
                    assessment_id,
                    q1,q2,q3,q4,q5,q6,q7,q8,q9,q10,q11,
                    q12,q13,q14,q15,q16,q17,q18,q19,q20,q21,q22
                ) VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
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
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    q1,q2,q3,q4,q5,q6,q7,q8,q9,q10,q11,
                    q12,q13,q14,q15,q16,q17,q18,q19,q20,q21,q22
                FROM assessment_responses
                WHERE assessment_id = %s
            """, (assessment_id,))
            row = cur.fetchone()
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
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO interventions (
                    student_code, profile, intervention_name,
                    intervention_description
                ) VALUES (%s, %s, %s, %s)
            """, (student_code, profile, intervention_name, intervention_description))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
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
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO study_interventions (
                    student_code, day_number, intervention_order,
                    profile, profile_score, profile_level,
                    overall_level, estimated_level,
                    intervention_name, intervention_description, intensity
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (student_code, day_number, intervention_order)
                DO UPDATE SET
                    profile = EXCLUDED.profile,
                    profile_score = EXCLUDED.profile_score,
                    profile_level = EXCLUDED.profile_level,
                    overall_level = EXCLUDED.overall_level,
                    estimated_level = EXCLUDED.estimated_level,
                    intervention_name = EXCLUDED.intervention_name,
                    intervention_description = EXCLUDED.intervention_description,
                    intensity = EXCLUDED.intensity,
                    shown_at = CURRENT_TIMESTAMP
            """, (
                student_code, int(day_number), int(intervention_order),
                profile, profile_score, profile_level,
                overall_level, estimated_level,
                intervention_name, intervention_description, intensity,
            ))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_study_interventions(student_code, day_number=None):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            query = """
                SELECT
                    id, student_code, day_number, intervention_order,
                    profile, profile_score, profile_level,
                    overall_level, estimated_level,
                    intervention_name, intervention_description,
                    intensity, shown_at
                FROM study_interventions
                WHERE student_code = %s
            """
            params = [student_code]
            if day_number is None:
                query += " ORDER BY day_number, intervention_order"
            else:
                query += " AND day_number = %s ORDER BY intervention_order"
                params.append(int(day_number))
            cur.execute(query, params)
            return cur.fetchall()
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
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO study_participants (
                    student_code, group_type, start_date,
                    end_date, status, consent
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (student_code) DO UPDATE SET
                    group_type = EXCLUDED.group_type,
                    start_date = EXCLUDED.start_date,
                    end_date = EXCLUDED.end_date,
                    status = EXCLUDED.status,
                    consent = EXCLUDED.consent
            """, (
                student_code, group_type, start_date, end_date,
                status, int(bool(consent)),
            ))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_study_participant(student_code):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, student_code, group_type, start_date,
                       end_date, status, consent, created_at
                FROM study_participants
                WHERE student_code = %s
            """, (student_code,))
            row = cur.fetchone()
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
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE study_participants
                SET status = 'completed', end_date = CURRENT_DATE::text
                WHERE student_code = %s
            """, (student_code,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
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
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO daily_logs (
                    student_code, day_number, action_status,
                    actual_minutes, coach_used, notes,
                    checkin_question, checkin_answer
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (student_code, day_number) DO UPDATE SET
                    action_status = EXCLUDED.action_status,
                    actual_minutes = EXCLUDED.actual_minutes,
                    coach_used = EXCLUDED.coach_used,
                    notes = EXCLUDED.notes,
                    checkin_question = EXCLUDED.checkin_question,
                    checkin_answer = EXCLUDED.checkin_answer,
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
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_daily_log(student_code, day_number):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    id, student_code, day_number, action_status,
                    actual_minutes, coach_used, notes, created_at,
                    checkin_question, checkin_answer
                FROM daily_logs
                WHERE student_code = %s AND day_number = %s
            """, (student_code, int(day_number)))
            return cur.fetchone()
    finally:
        conn.close()


# ================================================================
# AI coach log
# ================================================================

def save_coach_log(student_code, day_number, student_message, coach_response):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO coach_logs (
                    student_code, day_number,
                    student_message, coach_response
                ) VALUES (%s, %s, %s, %s)
            """, (student_code, int(day_number), student_message, coach_response))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()