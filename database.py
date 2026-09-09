import sqlite3
from datetime import date, datetime

from config import DB_PATH


# ================================================================
# Database connection
# ================================================================

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ================================================================
# Database initialization
# ================================================================

def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()

    # ============================================================
    # Existing application tables
    # ============================================================

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
            major TEXT
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

    # ============================================================
    # Pilot study participant table
    # ============================================================

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

    # ============================================================
    # Individual questionnaire responses
    # ============================================================
    #
    # This table stores Q1-Q22 for each assessment.
    #
    # The main assessments table stores:
    #   total_score
    #   level
    #
    # This table stores:
    #   q1 ... q22
    #
    # This allows exact comparison between pretest and posttest.
    # ============================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assessment_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            assessment_id INTEGER UNIQUE,

            q1 INTEGER,
            q2 INTEGER,
            q3 INTEGER,
            q4 INTEGER,
            q5 INTEGER,
            q6 INTEGER,
            q7 INTEGER,
            q8 INTEGER,
            q9 INTEGER,
            q10 INTEGER,
            q11 INTEGER,
            q12 INTEGER,
            q13 INTEGER,
            q14 INTEGER,
            q15 INTEGER,
            q16 INTEGER,
            q17 INTEGER,
            q18 INTEGER,
            q19 INTEGER,
            q20 INTEGER,
            q21 INTEGER,
            q22 INTEGER,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (assessment_id)
                REFERENCES assessments(id)
        )
    """)

    # ============================================================
    # Study interventions
    # ============================================================
    #
    # Stores exactly what the system showed to the student.
    #
    # intervention_order:
    #   1 = primary intervention
    #   2 = secondary intervention
    #
    # This is important for the research because later we can
    # determine exactly which intervention each participant received.
    # ============================================================

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

            UNIQUE(
                student_code,
                day_number,
                intervention_order
            )
        )
    """)

    # ============================================================
    # Daily intervention/action log
    # ============================================================
    #
    # We do NOT administer the 22-item questionnaire every day.
    #
    # Instead, the participant records:
    #   not_started
    #   partial
    #   completed
    #
    # plus actual minutes and optional notes.
    # ============================================================

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

            UNIQUE(
                student_code,
                day_number
            )
        )
    """)

    # ============================================================
    # AI Coach interaction log
    # ============================================================

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

    conn.commit()
    conn.close()


# ================================================================
# Existing assessment functions
# ================================================================

def save_assessment(
    student_code,
    assessment_type,
    total_score,
    level
):
    """
    Save one assessment.

    assessment_type examples:
        pretest
        posttest

    Returns:
        assessment_id
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO assessments (
            student_code,
            assessment_type,
            total_score,
            level
        )
        VALUES (?, ?, ?, ?)
    """, (
        student_code,
        assessment_type,
        total_score,
        level
    ))

    assessment_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return assessment_id


def save_intervention(
    student_code,
    profile,
    intervention_name,
    intervention_description
):
    """
    Existing intervention-saving function.
    Kept for compatibility with the current application.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO interventions (
            student_code,
            profile,
            intervention_name,
            intervention_description
        )
        VALUES (?, ?, ?, ?)
    """, (
        student_code,
        profile,
        intervention_name,
        intervention_description
    ))

    conn.commit()
    conn.close()


# ================================================================
# Questionnaire response helpers
# ================================================================

def _normalize_answers(answers):
    """
    Convert questionnaire answers into a list of exactly 22 values.

    Accepted formats:

    1) List / tuple:

       [
           q1, q2, q3, ..., q22
       ]

    2) Dictionary:

       {
           "q1": 1,
           "q2": 2,
           ...
           "q22": 5
       }
    """

    if isinstance(answers, dict):

        values = [
            answers.get(f"q{i}")
            for i in range(1, 23)
        ]

    else:

        values = list(answers)

    if len(values) != 22:

        raise ValueError(
            "answers must contain exactly 22 questionnaire responses"
        )

    return values


# ================================================================
# Save questionnaire responses
# ================================================================

def save_assessment_responses(
    assessment_id,
    answers
):
    """
    Save Q1-Q22 responses for an existing assessment.
    """

    values = _normalize_answers(answers)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO assessment_responses (
            assessment_id,

            q1,
            q2,
            q3,
            q4,
            q5,
            q6,
            q7,
            q8,
            q9,
            q10,
            q11,
            q12,
            q13,
            q14,
            q15,
            q16,
            q17,
            q18,
            q19,
            q20,
            q21,
            q22
        )
        VALUES (
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?
        )
    """, (
        assessment_id,
        *values
    ))

    conn.commit()
    conn.close()


# ================================================================
# Save assessment + Q1-Q22 atomically
# ================================================================

def save_assessment_with_responses(
    student_code,
    assessment_type,
    total_score,
    level,
    answers
):
    """
    Save assessment information and Q1-Q22 responses together.

    This is the preferred function for:
        pretest
        posttest

    If an error occurs, neither the assessment nor its responses
    will be saved.
    """

    values = _normalize_answers(answers)

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            INSERT INTO assessments (
                student_code,
                assessment_type,
                total_score,
                level
            )
            VALUES (?, ?, ?, ?)
        """, (
            student_code,
            assessment_type,
            total_score,
            level
        ))

        assessment_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO assessment_responses (
                assessment_id,

                q1,
                q2,
                q3,
                q4,
                q5,
                q6,
                q7,
                q8,
                q9,
                q10,
                q11,
                q12,
                q13,
                q14,
                q15,
                q16,
                q17,
                q18,
                q19,
                q20,
                q21,
                q22
            )
            VALUES (
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?
            )
        """, (
            assessment_id,
            *values
        ))

        conn.commit()

        return assessment_id

    except Exception:

        conn.rollback()

        raise

    finally:

        conn.close()


# ================================================================
# Get assessment
# ================================================================

def get_assessment(
    student_code,
    assessment_type
):
    """
    Return the most recent assessment of a given type.

    Example:

        get_assessment("P001", "pretest")
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            student_code,
            assessment_type,
            total_score,
            level,
            created_at
        FROM assessments
        WHERE student_code = ?
          AND assessment_type = ?
        ORDER BY id DESC
        LIMIT 1
    """, (
        student_code,
        assessment_type
    ))

    row = cursor.fetchone()

    conn.close()

    return row


def has_assessment(
    student_code,
    assessment_type
):
    """
    Check whether a student has a given assessment.
    """

    return (
        get_assessment(
            student_code,
            assessment_type
        )
        is not None
    )


# ================================================================
# Get Q1-Q22 responses
# ================================================================
def get_assessment_responses(assessment_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            assessment_id,
            q1,
            q2,
            q3,
            q4,
            q5,
            q6,
            q7,
            q8,
            q9,
            q10,
            q11,
            q12,
            q13,
            q14,
            q15,
            q16,
            q17,
            q18,
            q19,
            q20,
            q21,
            q22
        FROM assessment_responses
        WHERE assessment_id = ?
    """, (assessment_id,))

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "assessment_id": row[0],
        "q1": row[1],
        "q2": row[2],
        "q3": row[3],
        "q4": row[4],
        "q5": row[5],
        "q6": row[6],
        "q7": row[7],
        "q8": row[8],
        "q9": row[9],
        "q10": row[10],
        "q11": row[11],
        "q12": row[12],
        "q13": row[13],
        "q14": row[14],
        "q15": row[15],
        "q16": row[16],
        "q17": row[17],
        "q18": row[18],
        "q19": row[19],
        "q20": row[20],
        "q21": row[21],
        "q22": row[22],
    }


# ================================================================
# Pilot participant registration
# ================================================================

def register_study_participant(
    student_code,
    group_type,
    start_date=None,
    end_date=None,
    consent=True,
    status="active"
):
    """
    Register a participant in the pilot study.

    group_type:
        "intervention"
        "control"

    Example:

        register_study_participant(
            student_code="P001",
            group_type="intervention",
            consent=True
        )
    """

    if group_type not in {
        "intervention",
        "control"
    }:

        raise ValueError(
            "group_type must be 'intervention' or 'control'"
        )

    # If no start date is supplied, use today.
    if start_date is None:

        start_date = date.today().isoformat()

    # Convert date/datetime objects to strings.
    if isinstance(
        start_date,
        (date, datetime)
    ):

        start_date = start_date.strftime(
            "%Y-%m-%d"
        )

    if isinstance(
        end_date,
        (date, datetime)
    ):

        end_date = end_date.strftime(
            "%Y-%m-%d"
        )

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO study_participants (
            student_code,
            group_type,
            start_date,
            end_date,
            status,
            consent
        )
        VALUES (
            ?,
            ?,
            ?,
            ?,
            ?,
            ?
        )

        ON CONFLICT(student_code)
        DO UPDATE SET
            group_type = excluded.group_type,
            start_date = excluded.start_date,
            end_date = excluded.end_date,
            status = excluded.status,
            consent = excluded.consent
    """, (
        student_code,
        group_type,
        start_date,
        end_date,
        status,
        int(bool(consent))
    ))

    conn.commit()
    conn.close()


# ================================================================
# Get participant
# ================================================================

def get_study_participant(student_code):
    """
    Return participant information as a dictionary.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            student_code,
            group_type,
            start_date,
            end_date,
            status,
            consent,
            created_at
        FROM study_participants
        WHERE student_code = ?
    """, (student_code,))

    row = cursor.fetchone()
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


# ================================================================
# Calculate study day

# ================================================================

def get_study_day(
    student_code,
    today=None
):
    """
    Calculate the current study day.

    Before start:
        0

    During study:
        1 ... 7

    After study:
        8 or greater

    Returns None if the participant does not exist.
    """

    participant = get_study_participant(
        student_code
    )

    if participant is None:
        return None

    if not participant["start_date"]:
        return None

    if today is None:
        today = date.today()

    if isinstance(today, str):

        today = date.fromisoformat(
            today
        )

    start = date.fromisoformat(
        participant["start_date"]
    )

    return (
        today - start
    ).days + 1


# ================================================================
# Complete participant
# ================================================================

def complete_study_participant(student_code):
    """
    Mark a participant as completed.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE study_participants
        SET
            status = 'completed',
            end_date = DATE('now')
        WHERE student_code = ?
    """, (student_code,))

    conn.commit()
    conn.close()


# ================================================================
# Save study intervention

# ================================================================

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
    intervention_order=1
):
    """
    Save a snapshot of an intervention shown to a participant.

    intervention_order:
        1 = primary intervention
        2 = secondary intervention
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO study_interventions (
            student_code,
            day_number,
            intervention_order,
            profile,
            profile_score,
            profile_level,
            overall_level,
            estimated_level,
            intervention_name,
            intervention_description,
            intensity
        )
        VALUES (
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?
        )

        ON CONFLICT(
            student_code,
            day_number,
            intervention_order
        )

        DO UPDATE SET
            profile = excluded.profile,
            profile_score = excluded.profile_score,
            profile_level = excluded.profile_level,
            overall_level = excluded.overall_level,
            estimated_level = excluded.estimated_level,
            intervention_name = excluded.intervention_name,
            intervention_description =
                excluded.intervention_description,
            intensity = excluded.intensity,
            shown_at = CURRENT_TIMESTAMP
    """, (
        student_code,
        day_number,
        intervention_order,
        profile,
        profile_score,
        profile_level,
        overall_level,
        estimated_level,
        intervention_name,
        intervention_description,
        intensity
    ))

    conn.commit()
    conn.close()


# ================================================================
# Get study interventions
# ================================================================

def get_study_interventions(
    student_code,
    day_number=None
):
    """
    Return saved intervention snapshots.

    If day_number is provided:
        return only that day's interventions.

    Otherwise:
        return all interventions for the participant.
    """

    conn = get_connection()
    cursor = conn.cursor()

    if day_number is None:

        cursor.execute("""
            SELECT
                id,
                student_code,
                day_number,
                intervention_order,
                profile,
                profile_score,
                profile_level,
                overall_level,
                estimated_level,
                intervention_name,
                intervention_description,
                intensity,
                shown_at
            FROM study_interventions
            WHERE student_code = ?
            ORDER BY
                day_number,
                intervention_order
        """, (
            student_code
        ))

    else:

        cursor.execute("""
            SELECT
                id,
                student_code,
                day_number,
                intervention_order,
                profile,
                profile_score,
                profile_level,
                overall_level,
                estimated_level,
                intervention_name,
                intervention_description,
                intensity,
                shown_at
            FROM study_interventions
            WHERE student_code = ?
              AND day_number = ?
            ORDER BY intervention_order
        """, (
            student_code,
            day_number
        ))

    rows = cursor.fetchall()

    conn.close()

    return rows


# ================================================================
# Save daily log
# ================================================================

def save_daily_log(
    student_code,
    day_number,
    action_status,
    actual_minutes=None,
    coach_used=False,
    notes=""
):
    """
    Save or update one daily activity record.

    action_status can be:

        "not_started"
        "partial"
        "completed"
    """

    allowed_statuses = {
        "not_started",
        "partial",
        "completed"
    }

    if action_status not in allowed_statuses:

        raise ValueError(
            "action_status must be one of: "
            "not_started, partial, completed"
        )

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO daily_logs (
            student_code,
            day_number,
            action_status,
            actual_minutes,
            coach_used,
            notes
        )
        VALUES (
            ?,
            ?,
            ?,
            ?,
            ?,
            ?
        )

        ON CONFLICT(
            student_code,
            day_number
        )

        DO UPDATE SET
            action_status = excluded.action_status,
            actual_minutes = excluded.actual_minutes,
            coach_used = excluded.coach_used,
            notes = excluded.notes,
            created_at = CURRENT_TIMESTAMP
    """, (
        student_code,
        day_number,
        action_status,
        actual_minutes,
        int(bool(coach_used)),
        notes
    ))

    conn.commit()
    conn.close()


# ================================================================
# Get daily log
# ================================================================

def get_daily_log(
    student_code,
    day_number
):
    """
    Return the daily log for a specific participant/day.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            student_code,
            day_number,
            action_status,
            actual_minutes,
            coach_used,
            notes,
            created_at
        FROM daily_logs
        WHERE student_code = ?
          AND day_number = ?
    """, (
        student_code,
        day_number
    ))

    row = cursor.fetchone()

    conn.close()

    return row


# ================================================================
# Save AI Coach interaction
# ================================================================

def save_coach_log(
    student_code,
    day_number,
    student_message,
    coach_response
):
    """
    Save an interaction with the AI Coach.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO coach_logs (
            student_code,
            day_number,
            student_message,
            coach_response
        )
        VALUES (
            ?,
            ?,
            ?,
            ?
        )
    """, (
        student_code,
        day_number,
        student_message,
        coach_response
    ))

    conn.commit()
    conn.close()