import json
from pathlib import Path

import joblib
import pandas as pd
import streamlit as st

from database import (
    initialize_database,
    get_connection,
    get_study_participant,
    get_study_day,
    has_assessment,
    get_assessment,
    get_assessment_responses,
    save_assessment_with_responses,
    save_intervention,
    save_study_intervention,
    get_study_interventions,
    save_daily_log,
    get_daily_log,
    save_coach_log,
)

try:
    from profile import create_profile
except ImportError:
    from procrastination_engine.profile import create_profile

from intervention_engine import choose_intervention, personalize_presentation
from ai_coach import ai_coach


# ============================================================
# Page / constants
# ============================================================

st.set_page_config(
    page_title="سامانه هوشمند مدیریت اهمال‌کاری",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    /* =========================
       RTL / Persian UI
       ========================= */
    .stApp {
        direction: rtl;
        text-align: right;
        background: #f5f7fb;
    }

    html, body, [class*="css"], .stMarkdown, .stTextInput,
    .stSelectbox, .stNumberInput, .stTextArea, .stRadio,
    .stCaption, .stAlert, .stButton, .stForm {
        direction: rtl !important;
        text-align: right !important;
        font-family: Tahoma, "Segoe UI", sans-serif;
    }

    .main .block-container {
        max-width: 1120px;
        padding-top: 1.5rem;
        padding-bottom: 4rem;
    }

    /* عنوان اصلی */
    .hero {
        background: linear-gradient(135deg, #ffffff 0%, #eef3ff 100%);
        border-radius: 22px;
        padding: 30px 32px;
        margin-bottom: 24px;
        border: 1px solid #e1e7f2;
        box-shadow: 0 8px 24px rgba(31, 41, 55, 0.06);
        text-align: right;
    }

    .hero h1 {
        margin: 0 0 10px 0;
        font-size: 2rem;
        font-weight: 800;
        line-height: 1.6;
    }

    .hero p {
        margin: 0;
        line-height: 2;
        color: #596273;
    }

    /* کارت‌های عمومی */
    .card {
        background: #ffffff;
        border-radius: 18px;
        padding: 22px 24px;
        margin: 16px 0;
        border: 1px solid #e3e8f0;
        box-shadow: 0 5px 18px rgba(31, 41, 55, 0.05);
        text-align: right;
    }

    .small {
        color: #687080;
        font-size: 0.9rem;
        line-height: 1.9;
    }

    /* کارت مداخله */
    .intervention {
        background: #ffffff;
        border: 1px solid #dfe5ef;
        border-radius: 18px;
        padding: 20px 22px;
        margin: 14px 0;
        box-shadow: 0 5px 16px rgba(31, 41, 55, 0.045);
        text-align: right;
    }

    .intervention-title {
        font-size: 1.15rem;
        font-weight: 800;
        margin-bottom: 8px;
        line-height: 1.8;
    }

    .action {
        padding: 10px 12px;
        margin: 7px 0;
        background: #f5f7fb;
        border-radius: 10px;
        line-height: 1.9;
    }

    .badge {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 999px;
        background: #eef2f8;
        margin: 4px;
        font-size: 0.85rem;
    }

    /* =========================
       Questionnaire
       ========================= */
    .questionnaire-intro {
        background: #ffffff;
        border: 1px solid #e3e8f0;
        border-radius: 16px;
        padding: 16px 20px;
        margin: 10px 0 18px 0;
        box-shadow: 0 4px 14px rgba(31, 41, 55, 0.04);
        line-height: 2;
    }

    /* متن سؤال */
    [data-testid="stRadio"] > label {
        direction: rtl !important;
        text-align: right !important;
        width: 100%;
        font-weight: 700 !important;
        line-height: 2 !important;
        margin-bottom: 8px !important;
    }

    /* گزینه‌های رادیویی */
    [data-testid="stRadio"] [role="radiogroup"] {
        direction: rtl !important;
        justify-content: flex-start !important;
        gap: 10px !important;
        flex-wrap: wrap !important;
    }

    [data-testid="stRadio"] [role="radio"] {
        direction: rtl !important;
        text-align: right !important;
        border: 1px solid #d9dfeb !important;
        border-radius: 12px !important;
        padding: 8px 12px !important;
        background: #fafbfe !important;
        transition: all 0.15s ease-in-out;
    }

    [data-testid="stRadio"] [role="radio"]:hover {
        border-color: #9aa9c2 !important;
        background: #f2f5fa !important;
    }

    /* ورودی‌ها و انتخابگرها */
    input, textarea, [role="combobox"] {
        direction: rtl !important;
        text-align: right !important;
    }

    /* دکمه‌ها */
    .stButton > button,
    .stFormSubmitButton > button {
        border-radius: 12px !important;
        min-height: 44px;
        font-weight: 700 !important;
        direction: rtl !important;
    }

    /* متریک‌ها */
    [data-testid="stMetric"] {
        direction: rtl !important;
        text-align: right !important;
        background: #ffffff;
        border: 1px solid #e3e8f0;
        border-radius: 14px;
        padding: 12px;
    }

    /* فاصله بهتر بین سؤال‌ها */
    [data-testid="stRadio"] {
        padding: 10px 0 16px 0;
        border-bottom: 1px solid #edf0f5;
    }

    /* پیام‌ها */
    [data-testid="stAlert"] {
        direction: rtl !important;
        text-align: right !important;
        border-radius: 12px !important;
    }

    /* موبایل */
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }

        .hero {
            padding: 22px 18px;
        }

        .hero h1 {
            font-size: 1.45rem;
        }

        [data-testid="stRadio"] [role="radiogroup"] {
            gap: 7px !important;
        }

        [data-testid="stRadio"] [role="radio"] {
            padding: 7px 9px !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

initialize_database()

MODEL_PATH = Path("models/random_forest_pipeline.joblib")

LEVEL_NAMES = {
    "low": "پایین",
    "medium": "متوسط",
    "high": "بالا",
    "پایین": "پایین",
    "متوسط": "متوسط",
    "بالا": "بالا",
}

PROFILE_NAMES = {
    "task_initiation": "تأخیر در شروع کار",
    "educational_content": "تأخیر در مصرف محتوای آموزشی",
    "deadline_time": "مدیریت مهلت و زمان",
    "participation": "حضور و مشارکت آنلاین",
    "task_difficulty": "مواجهه با دشواری تکلیف",
    "digital_distraction": "حواس‌پرتی دیجیتال",
    "help_seeking": "تأخیر در کمک‌خواهی از استاد",
    "group_activity": "تأخیر در فعالیت گروهی",
    "stress_guilt": "استرس و احساس گناه همراه با تعلل",
    "general_procrastination": "اهمال‌کاری عمومی",
}

QUESTIONS = [
    "تماشای فیلم‌های ضبط‌شدهٔ دروس را تا روزهای پایانی نیمسال به تأخیر می‌اندازم.",
    "هنگام برگزاری کلاس مجازی زنده، کارهای غیردرسی (مثل وبگردی، شبکه‌های اجتماعی) انجام می‌دهم.",
    "تکالیف آنلاین را معمولاً شب قبل از ددلاین شروع می‌کنم.",
    "برای مطالعهٔ منابع الکترونیکی ارائه شده توسط استاد، انگیزهٔ کافی ندارم و مدام آن را به بعد موکول می‌کنم.",
    "در طول آزمون‌های آنلاین، زمان را مدیریت نمی‌کنم و پاسخ‌گویی را به دقیقه‌های آخر می‌سپارم.",
    "حضور در جلسات همزمان مجازی را با عذرهایی (مشکل اینترنت، خواب‌ماندن) از دست می‌دهم.",
    "وقتی تکلیفی دشوار و وقت‌گیر است، شروع آن را به تأخیر می‌اندازم.",
    "برای مشارکت در بحث‌های کلاس مجازی، اغلب دیر اقدام می‌کنم یا اصلاً اقدامی نمی‌کنم.",
    "مطالعهٔ فایل‌های درسی (PDF، اسلایدها) را آنقدر به تعویق می‌اندازم که انباشته شوند.",
    "برنامهٔ هفتگی مشخصی برای تماشای محتوای آفلاین دروس ندارم و کارها را به روزهای آخر موکول می‌کنم.",
    "در فضای آموزش الکترونیکی، به دلیل نبود نظارت مستقیم استاد، انجام به موقع وظایف برایم دشوار است.",
    "تمرینات آنلاین تعاملی را معمولاً پس از اتمام مهلت مجاز یا با تأخیر زیاد ارسال می‌کنم.",
    "ترجیح می‌دهم به جای مطالعهٔ درس، کارهای زودبازده تفریحی (بازی، فیلم) انجام دهم.",
    "جمع‌آوری مطالب ترم را تا شب امتحان یا تحویل پروژه نهایی به تعویق می‌اندازم.",
    "وقتی استاد تکلیف گروهی آنلاین تعیین می‌کند، سهم خود را دیرتر از توافق گروه تحویل می‌دهم.",
    "برای رفع اشکال از استاد (ایمیل یا تالار گفتگو)، معمولاً آنقدر تعلل می‌کنم که دیگر فرصت باقی نمی‌ماند.",
    "حین تماشای فیلم جلسات مجازی، به سادگی تمرکزم را از دست می‌دهم و آن را متوقف کرده و بعداً دنبال می‌کنم (که غالباً فراموش می‌شود).",
    "نسبت به عقب افتادن از برنامهٔ درسی در آموزش مجازی احساس گناه و استرس دارم، اما باز هم تعلل می‌کنم.",
    "به طور کلی، عادت دارم کارهای تحصیلی در بستر الکترونیکی را به آخرین لحظات موکول کنم.",
    "بلافاصله پس از دریافت اعلان تکلیف، کار را شروع می‌کنم.",
    "در کلاس مجازی زنده، تمرکز کامل دارم و حاشیه نمی‌روم.",
    "تکالیف گروهی را پیش از موعد مقرر به همگروهی‌هایم تحویل می‌دهم.",
]

REVERSE_ITEMS = {20, 21, 22}

OPTIONS = [
    "هرگز",
    "به‌ندرت",
    "گاهی",
    "اغلب",
    "همیشه",
]


# ============================================================
# Helpers
# ============================================================

@st.cache_resource
def get_model():
    if not MODEL_PATH.exists():
        return None
    try:
        return joblib.load(MODEL_PATH)
    except Exception:
        return None


def build_model_input(student_data):
    gender_code = {"زن": 0, "مرد": 1}[student_data["gender"]]
    degree_code = {
        "کارشناسی": 1,
        "کارشناسی ارشد": 2,
        "دکتری": 3,
    }[student_data["degree"]]
    use_code = {
        "کمتر از ۲ ساعت": 1,
        "۲ تا ۴ ساعت": 2,
        "۴ تا ۶ ساعت": 3,
        "بیشتر از ۶ ساعت": 4,
    }[student_data["daily_use"]]

    return pd.DataFrame([{
        "Age_Num": int(student_data["age"]),
        "جنسیت": gender_code,
        "مقطع": degree_code,
        "ترمتحصیلی": int(student_data["semester"]),
        "استفاده": use_code,
        "دانشگاه": student_data["university"],
        "رشتهتحصیلی": student_data["major"].strip(),
    }])


def predict_level(student_data):
    model = get_model()
    if model is None:
        return None

    try:
        x = build_model_input(student_data)
        prediction = model.predict(x)[0]

        probabilities = {}
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(x)[0]
            classes = model.classes_
            probabilities = {
                str(cls): float(prob)
                for cls, prob in zip(classes, proba)
            }

        return {
            "level": str(prediction),
            "probabilities": probabilities,
        }
    except Exception:
        return None


def calculate_total_score(answers):
    values = [int(answers[f"q{i}"]) for i in range(1, 23)]

    for item in REVERSE_ITEMS:
        index = item - 1
        values[index] = 6 - values[index]

    return float(sum(values))


def classify_overall_level(score):
    # Operational cut-points derived from the thesis sample distribution.
    if score <= 51:
        return "low"
    if score <= 66.6741:
        return "medium"
    return "high"


def normalize_level(level):
    mapping = {
        "پایین": "low",
        "متوسط": "medium",
        "بالا": "high",
        "low": "low",
        "medium": "medium",
        "high": "high",
    }
    return mapping.get(str(level).strip().lower(), str(level).strip().lower())


def profile_label(profile):
    return PROFILE_NAMES.get(profile, profile or "الگوی رفتاری")


def save_student(student_data):
    """Persist the seven demographic/educational fields in the existing students table."""
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO students (
                student_code, age, gender, degree, semester,
                use_level, university, major
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(student_code)
            DO UPDATE SET
                age = excluded.age,
                gender = excluded.gender,
                degree = excluded.degree,
                semester = excluded.semester,
                use_level = excluded.use_level,
                university = excluded.university,
                major = excluded.major
            """,
            (
                student_data["student_code"],
                int(student_data["age"]),
                student_data["gender"],
                student_data["degree"],
                int(student_data["semester"]),
                student_data["daily_use"],
                student_data["university"],
                student_data["major"],
            ),
        )
        conn.commit()
    finally:
        conn.close()


def load_student(student_code):
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT
                student_code, age, gender, degree, semester,
                use_level, university, major
            FROM students
            WHERE student_code = ?
            """,
            (student_code,),
        ).fetchone()
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
    }


def row_to_intervention(row):
    """Convert a study_interventions DB row into the minimal intervention object."""
    return {
        "profile": row[4],
        "profile_name": profile_label(row[4]),
        "profile_score": row[5],
        "profile_level": row[6],
        "overall_level": row[7],
        "estimated_level": row[8],
        "name": row[9],
        "description": row[10],
        "intensity": row[11],
        "actions": [],
        "presentation": {},
    }


def render_intervention(intervention, index=1):
    name = intervention.get("name", "مداخله پیشنهادی")
    description = intervention.get("description", "")
    profile = profile_label(intervention.get("profile"))
    score = intervention.get("profile_score")
    intensity = LEVEL_NAMES.get(
        intervention.get("intensity", "medium"),
        intervention.get("intensity", "medium"),
    )

    action_html = "".join(
        f'<div class="action">✓ {action}</div>'
        for action in (intervention.get("actions") or [])
    )

    presentation = intervention.get("presentation") or {}
    notes = [
        presentation.get("detail_note"),
        presentation.get("time_note"),
    ]
    notes = [x for x in notes if x]
    notes_html = (
        f'<div class="small">نحوه ارائه: {" ".join(notes)}</div>'
        if notes
        else ""
    )

    score_html = (
        f' | امتیاز الگو: {round(float(score), 2)}'
        if score is not None
        else ""
    )

    st.markdown(
        f"""
        <div class="intervention">
            <div class="intervention-title">{index}. {name}</div>
            <div class="small">
                مرتبط با: <b>{profile}</b>{score_html} | شدت: {intensity}
            </div>
            <p>{description}</p>
            {action_html}
            {notes_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_student_context(student):
    st.markdown(
        f"""
        <div class="card">
            <span class="badge">سن: {student["age"]}</span>
            <span class="badge">جنسیت: {student["gender"]}</span>
            <span class="badge">مقطع: {student["degree"]}</span>
            <span class="badge">ترم: {student["semester"]}</span>
            <span class="badge">استفاده روزانه: {student["daily_use"]}</span>
            <span class="badge">دانشگاه: {student["university"]}</span>
            <span class="badge">رشته: {student["major"]}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def questionnaire_form(form_key, title):
    st.subheader(title)
    st.markdown(
        """
        <div class="questionnaire-intro">
            <b>راهنمای پاسخ‌گویی:</b>
            برای هر عبارت، میزان تکرار رفتار خود را با یکی از گزینه‌های
            <b>هرگز، به‌ندرت، گاهی، اغلب، همیشه</b> مشخص کنید.
        </div>
        """,
        unsafe_allow_html=True,
    )

    answers = {}

    with st.form(form_key):
        for i, question in enumerate(QUESTIONS, start=1):
            answers[f"q{i}"] = st.radio(
                f"{i}. {question}",
                OPTIONS,
                index=2,
                horizontal=True,
                key=f"{form_key}_q{i}",
            )

        submitted = st.form_submit_button(
            "ثبت پاسخ‌ها",
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return None

    # Convert Persian frequency labels to scores 1..5.
    numeric = {
        f"q{i}": OPTIONS.index(answers[f"q{i}"]) + 1
        for i in range(1, 23)
    }
    return numeric


def to_profile_answers(answers):
    """Normalize questionnaire keys for the behavioral profile engine.

    The UI/database use q1..q22, while profile.py expects Q1..Q22
    and reverse-scored items such as Q20R are resolved internally.
    """
    return {f"Q{i}": answers[f"q{i}"] for i in range(1, 23)}


def calculate_intervention_result(student, answers):
    total_score = calculate_total_score(answers)
    overall_level = classify_overall_level(total_score)

    profile_result = create_profile(to_profile_answers(answers))

    ml_result = predict_level(student)
    estimated_level = (
        ml_result["level"] if ml_result is not None else overall_level
    )

    decision = choose_intervention(
        answers,
        overall_level=estimated_level,
        profile_result=profile_result,
    )

    interventions = [
        personalize_presentation(item, student)
        for item in decision.get("interventions", [])
    ]

    primary = interventions[0] if interventions else None

    return {
        "total_score": total_score,
        "overall_level": overall_level,
        "profile_result": profile_result,
        "ml_result": ml_result,
        "estimated_level": estimated_level,
        "interventions": interventions,
        "primary": primary,
    }


def save_pretest(student, answers):
    result = calculate_intervention_result(student, answers)

    assessment_id = save_assessment_with_responses(
        student["student_code"],
        "pretest",
        result["total_score"],
        result["overall_level"],
        answers,
    )

    return result, assessment_id


def save_posttest(student, answers):
    result = calculate_intervention_result(student, answers)

    assessment_id = save_assessment_with_responses(
        student["student_code"],
        "posttest",
        result["total_score"],
        result["overall_level"],
        answers,
    )

    return result, assessment_id


def save_day1_interventions(student, result):
    for index, intervention in enumerate(result["interventions"][:2], start=1):
        save_intervention(
            student["student_code"],
            intervention.get("profile", ""),
            intervention.get("name", ""),
            intervention.get("description", ""),
        )

        save_study_intervention(
            student_code=student["student_code"],
            day_number=1,
            profile=intervention.get("profile", ""),
            profile_score=intervention.get("profile_score"),
            profile_level=intervention.get("profile_level", ""),
            overall_level=result["overall_level"],
            estimated_level=result["estimated_level"],
            intervention_name=intervention.get("name", ""),
            intervention_description=intervention.get("description", ""),
            intensity=intervention.get("intensity", "medium"),
            intervention_order=index,
        )


def render_result_summary(result):
    c1, c2, c3 = st.columns(3)
    c1.metric("نمره کل", f'{result["total_score"]:.1f} از 110')
    c2.metric("سطح پرسشنامه", LEVEL_NAMES.get(result["overall_level"], result["overall_level"]))
    c3.metric("برآورد مدل", LEVEL_NAMES.get(result["estimated_level"], result["estimated_level"]))

    ml = result.get("ml_result")
    if ml and ml.get("probabilities"):
        p = ml["probabilities"]
        st.caption(
            "احتمال‌های مدل: "
            + " | ".join(
                f"{LEVEL_NAMES.get(k, k)}: {v:.1%}"
                for k, v in p.items()
            )
        )


# ============================================================
# Session initialization
# ============================================================

for key, default in {
    "student_code": "",
    "student": None,
    "participant": None,
    "pending_participant_code": "",
    "pending_participant": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


def render_participant_info_form(code, participant):
    """Collect and persist the seven demographic/educational model inputs."""
    st.subheader("تکمیل اطلاعات شرکت‌کننده")
    st.caption(
        "این اطلاعات برای اجرای مدل و شخصی‌سازی نحوه ارائه مداخله "
        "ثبت می‌شوند. کد پژوهشی ناشناس باقی می‌ماند."
    )

    with st.form("participant_info_form"):
        c1, c2 = st.columns(2)
        with c1:
            age = st.number_input("سن", min_value=15, max_value=80, value=20, step=1)
            gender = st.selectbox("جنسیت", ["زن", "مرد"])
            degree = st.selectbox("مقطع تحصیلی", ["کارشناسی", "کارشناسی ارشد", "دکتری"])
            semester = st.number_input("ترم تحصیلی", min_value=1, max_value=20, value=1, step=1)
        with c2:
           daily_use = st.selectbox(
    "میزان استفاده روزانه از آموزش الکترونیکی",
    [
        "کمتر از ۲ ساعت",
        "از ۲ تا ۴ ساعت",
        "از ۴ تا ۶ ساعت",
        "بیشتر از ۶ ساعت",
    ],
)
            university = st.selectbox("نوع دانشگاه", ["آزاد", "دولتی", "غیرانتفاعی", "مجازی"])
            major = st.text_input("رشته تحصیلی", placeholder="مثلاً مهندسی کامپیوتر")

        submitted = st.form_submit_button("ثبت اطلاعات و ادامه", type="primary", use_container_width=True)

    if not submitted:
        return

    if not major.strip():
        st.error("رشته تحصیلی را وارد کنید.")
        return

    student_data = {
        "student_code": code,
        "age": int(age),
        "gender": gender,
        "degree": degree,
        "semester": int(semester),
        "daily_use": daily_use,
        "university": university,
        "major": major.strip(),
    }

    try:
        save_student(student_data)
        st.session_state.student_code = code
        st.session_state.participant = participant
        st.session_state.student = student_data
        st.success("اطلاعات شرکت‌کننده با موفقیت ثبت شد.")
        st.rerun()
    except Exception as exc:
        st.error(f"ثبت اطلاعات شرکت‌کننده انجام نشد: {exc}")


# ============================================================
# Login / participant identification
# ============================================================

st.markdown(
    """
    <div class="hero">
        <h1>سامانه هوشمند مدیریت اهمال‌کاری</h1>
        <p>
        این نسخه برای اجرای پایلوت پژوهشی طراحی شده است.
        اطلاعات با یک کد ناشناس ذخیره می‌شود.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# The participant login and the participant-information form must survive
# Streamlit reruns. A form submission causes a fresh script run, so the
# selected participant is kept in session_state before showing the form.
if not st.session_state.student_code:
    st.subheader("ورود به مطالعه")

    # If a participant was already validated but has not yet completed
    # the seven demographic/educational fields, show the form directly.
    pending_code = st.session_state.get("pending_participant_code", "")
    pending_participant = st.session_state.get("pending_participant")

    if pending_code and pending_participant:
        existing_student = load_student(pending_code)

        if existing_student is not None:
            st.session_state.student_code = pending_code
            st.session_state.participant = pending_participant
            st.session_state.student = existing_student
            st.session_state.pending_participant_code = ""
            st.session_state.pending_participant = None
            st.rerun()
        else:
            st.info(f"کد پژوهشی {pending_code} تأیید شد. ابتدا اطلاعات شرکت‌کننده را تکمیل کنید.")
            render_participant_info_form(pending_code, pending_participant)

    else:
        code = st.text_input(
            "کد پژوهشی",
            placeholder="مثلاً P101",
            help="این کد باید قبلاً توسط پژوهشگر در جدول مطالعه ثبت شده باشد.",
            key="login_code",
        ).strip().upper()

        if st.button("ورود", type="primary", use_container_width=True):
            if not code:
                st.error("کد پژوهشی را وارد کنید.")
            else:
                participant = get_study_participant(code)

                if participant is None:
                    st.error(
                        "این کد در مطالعه ثبت نشده است. "
                        "کد را از پژوهشگر دریافت کنید."
                    )
                elif not participant["consent"]:
                    st.error("رضایت شرکت در مطالعه برای این کد ثبت نشده است.")
                elif participant["status"] == "completed":
                    student = load_student(code)

                    if student is None:
                        st.warning(
                            "این کد در مطالعه ثبت شده، اما اطلاعات جمعیت‌شناختی/آموزشی آن ثبت نشده است."
                        )
                        st.session_state.pending_participant_code = code
                        st.session_state.pending_participant = participant
                        st.rerun()
                    else:
                        st.info("این شرکت‌کننده قبلاً مطالعه را کامل کرده است.")
                        st.session_state.student_code = code
                        st.session_state.participant = participant
                        st.session_state.student = student
                        st.rerun()
                else:
                    student = load_student(code)

                    if student is None:
                        st.session_state.pending_participant_code = code
                        st.session_state.pending_participant = participant
                        st.rerun()
                    else:
                        st.session_state.student_code = code
                        st.session_state.participant = participant
                        st.session_state.student = student
                        st.rerun()

    st.stop()


# ============================================================
# Load persistent participant context
# ============================================================

student_code = st.session_state.student_code
participant = get_study_participant(student_code)
student = load_student(student_code)

if participant is None or student is None:
    st.error("اطلاعات شرکت‌کننده کامل نیست.")
    st.session_state.student_code = ""
    st.stop()

st.session_state.participant = participant
st.session_state.student = student

render_student_context(student)

study_day = get_study_day(student_code)

if study_day is None:
    st.error("تاریخ شروع مطالعه برای این شرکت‌کننده مشخص نیست.")
    st.stop()

st.caption(f"کد پژوهشی: {student_code} | روز مطالعه: {study_day} از 7")


# ============================================================
# Completed
# ============================================================

if participant["status"] == "completed":
    st.success("این مطالعه برای این کد پژوهشی تکمیل شده است.")
    st.info("از همکاری شما سپاسگزاریم.")
    st.stop()


# ============================================================
# Pretest — BOTH GROUPS
# ============================================================

if not has_assessment(student_code, "pretest"):
    st.warning(
        "مرحله اول مطالعه: پیش‌آزمون. "
        "هر دو گروه مداخله و کنترل باید این مرحله را تکمیل کنند."
    )

    answers = questionnaire_form(
        "pretest_form",
        "پیش‌آزمون اهمال‌کاری",
    )

    if answers is not None:
        try:
            result, assessment_id = save_pretest(student, answers)

            if participant["group_type"] == "intervention":
                save_day1_interventions(student, result)

            st.session_state["pretest_saved"] = True
            st.success("پیش‌آزمون با موفقیت ثبت شد.")
            render_result_summary(result)

            if participant["group_type"] == "intervention":
                st.info(
                    "گروه شما در بخش مداخله قرار دارد. "
                    "از این مرحله به بعد، سامانه بر اساس الگوی رفتاری ثبت‌شده "
                    "مداخله عملیاتی را نمایش می‌دهد."
                )
            else:
                st.info(
                    "پیش‌آزمون ثبت شد. در طول این هفته مداخله اختصاصی سامانه "
                    "برای گروه کنترل نمایش داده نمی‌شود."
                )

            st.rerun()

        except Exception as exc:
            st.error(f"ثبت پیش‌آزمون انجام نشد: {exc}")

    st.stop()


# ============================================================
# Day 1–7 daily phase
# ============================================================

if 1 <= study_day <= 7:

    if participant["group_type"] == "control":
        st.subheader(f"گروه کنترل — روز {study_day}")

        st.markdown(
            """
            <div class="card">
                <h3>روال معمول آموزشی</h3>
                <p>
                در این مرحله مداخله اختصاصی سامانه نمایش داده نمی‌شود.
                روال معمول آموزشی خود را ادامه دهید.
                </p>
                <p class="small">
                پس‌آزمون در پایان روز هفتم در همین سامانه انجام خواهد شد.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    else:
        st.subheader(f"گروه مداخله — روز {study_day}")

        # The intervention is fixed from day 1 so the pilot does not
        # silently change intervention type during the week.
        saved = get_study_interventions(student_code, day_number=1)

        if not saved:
            st.error("مداخله روز اول در پایگاه داده پیدا نشد.")
        else:
            st.markdown(
                """
                <div class="card">
                    <h3>مداخله شخصی‌سازی‌شده</h3>
                    <p class="small">
                    نوع مداخله بر اساس الگوی رفتاری استخراج‌شده از پرسشنامه
                    انتخاب شده است. ویژگی‌های جمعیت‌شناختی/آموزشی برای
                    شخصی‌سازی زمینه و نحوه ارائه استفاده می‌شوند و به‌تنهایی
                    تعیین‌کننده نوع مداخله نیستند.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Reconstruct presentation only for display; the intervention
            # identity/name/description remain the saved day-1 snapshot.
            pretest = get_assessment(student_code, "pretest")
            pretest_answers = None

            if pretest:
                pretest_answers = get_assessment_responses(pretest[0])

            reconstructed = None
            if pretest_answers:
                reconstructed = calculate_intervention_result(
                    student,
                    pretest_answers,
                )

            for index, row in enumerate(saved, start=1):
                intervention = row_to_intervention(row)

                if reconstructed and index <= len(reconstructed["interventions"]):
                    dynamic = reconstructed["interventions"][index - 1]
                    intervention["actions"] = dynamic.get("actions") or []
                    intervention["presentation"] = dynamic.get("presentation") or []

                render_intervention(intervention, index)

            st.divider()

            existing_log = get_daily_log(student_code, study_day)

            with st.form(f"daily_log_{study_day}"):
                status_labels = {
                    "not_started": "هنوز شروع نکردم",
                    "partial": "بخشی از آن را انجام دادم",
                    "completed": "کامل انجام دادم",
                }

                status_values = list(status_labels.keys())
                default_status = (
                    existing_log[3]
                    if existing_log and existing_log[3] in status_values
                    else "not_started"
                )

                status = st.radio(
                    "وضعیت اجرای فعالیت امروز",
                    status_values,
                    index=status_values.index(default_status),
                    format_func=lambda x: status_labels[x],
                )

                minutes = st.number_input(
                    "مدت اجرای فعالیت (دقیقه)",
                    min_value=0,
                    max_value=600,
                    value=int(existing_log[4] or 0) if existing_log else 0,
                    step=5,
                )

                notes = st.text_area(
                    "یادداشت اختیاری",
                    value=existing_log[6] or "" if existing_log else "",
                )

                submitted = st.form_submit_button(
                    "ثبت فعالیت امروز",
                    type="primary",
                    use_container_width=True,
                )

            if submitted:
                save_daily_log(
                    student_code=student_code,
                    day_number=study_day,
                    action_status=status,
                    actual_minutes=int(minutes),
                    coach_used=bool(existing_log[5]) if existing_log else False,
                    notes=notes,
                )
                st.success("گزارش فعالیت امروز ثبت شد.")

    # --------------------------------------------------------
    # AI Coach — available to intervention group only
    # --------------------------------------------------------

    if participant["group_type"] == "intervention":
        st.divider()
        st.subheader("مربی هوشمند")

        saved = get_study_interventions(student_code, day_number=1)

        if saved:
            primary = row_to_intervention(saved[0])

            student_message = st.text_area(
                "اگر درباره اجرای فعالیت امروز سؤال یا مشکلی داری، بنویس:",
                placeholder="مثلاً شروع کار برایم سخت است و مدام آن را عقب می‌اندازم.",
                key=f"coach_message_{study_day}",
            )

            if st.button(
                "دریافت پیشنهاد مربی",
                key=f"coach_button_{study_day}",
                type="primary",
            ):
                if not student_message.strip():
                    st.warning("ابتدا پیام خود را بنویس.")
                else:
                    try:
                        response = ai_coach(
                            level=primary["estimated_level"],
                            dominant_profile=primary["profile"],
                            intervention_name=primary["name"],
                            intervention_description=primary["description"],
                            student_message=student_message.strip(),
                            student_context=student,
                        )

                        st.markdown(
                            f"""
                            <div class="card">
                                <h4>پیشنهاد مربی</h4>
                                <p>{response}</p>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        save_coach_log(
                            student_code=student_code,
                            day_number=study_day,
                            student_message=student_message.strip(),
                            coach_response=response,
                        )

                        existing = get_daily_log(student_code, study_day)
                        save_daily_log(
                            student_code=student_code,
                            day_number=study_day,
                            action_status=(
                                existing[3] if existing else "not_started"
                            ),
                            actual_minutes=(
                                existing[4] if existing else 0
                            ),
                            coach_used=True,
                            notes=(
                                existing[6] if existing else ""
                            ),
                        )

                    except Exception as exc:
                        st.error(f"مربی هوشمند در دسترس نیست: {exc}")


# ============================================================
# Posttest — BOTH GROUPS after day 7
# ============================================================

if study_day >= 7:

    st.divider()
    st.subheader("پس‌آزمون")

    if has_assessment(student_code, "posttest"):
        posttest = get_assessment(student_code, "posttest")

        st.success("پس‌آزمون قبلاً ثبت شده است.")

        if posttest:
            st.metric(
                "نمره پس‌آزمون",
                f"{posttest[2]:.1f} از 110",
            )

        if participant["status"] != "completed":
            # Completion is explicit after the posttest exists.
            from database import complete_study_participant
            complete_study_participant(student_code)

        st.info("مطالعه برای این کد پژوهشی تکمیل شد.")
        st.stop()

    st.info(
        "پس‌آزمون باید با همان 22 عبارت اجرا شود. "
        "این آزمون برای هر دو گروه یکسان است."
    )

    post_answers = questionnaire_form(
        "posttest_form",
        "پس‌آزمون اهمال‌کاری",
    )

    if post_answers is not None:
        try:
            post_result, assessment_id = save_posttest(
                student,
                post_answers,
            )

            from database import complete_study_participant
            complete_study_participant(student_code)

            st.success("پس‌آزمون با موفقیت ثبت شد.")

            c1, c2 = st.columns(2)
            c1.metric(
                "نمره پس‌آزمون",
                f'{post_result["total_score"]:.1f} از 110',
            )
            c2.metric(
                "سطح پس‌آزمون",
                LEVEL_NAMES.get(
                    post_result["overall_level"],
                    post_result["overall_level"],
                ),
            )

            st.info(
                "سپاسگزاریم. داده‌های پیش‌آزمون، پس‌آزمون و فعالیت‌های ثبت‌شده "
                "برای تحلیل پژوهشی ذخیره شدند."
            )

        except Exception as exc:
            st.error(f"ثبت پس‌آزمون انجام نشد: {exc}")

