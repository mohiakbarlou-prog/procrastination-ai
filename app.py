import json
import html
from io import BytesIO
from datetime import date
from pathlib import Path

import joblib
import pandas as pd
import streamlit as st

from database import (
    initialize_database,
    get_connection,
    get_study_participant,
    register_study_participant,
    get_study_day,
    get_study_date,
    jalali_from_gregorian,
    to_persian_digits,
    jalali_to_gregorian,
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
    save_student,
    load_student,
    verify_researcher_code,
    complete_study_participant,
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
        background: #f2f8f4;
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
        background: linear-gradient(135deg, #ffffff 0%, #edf8f1 100%);
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

    /* کارت برنامه */
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
        background: #f2f8f4;
        border-radius: 10px;
        line-height: 1.9;
    }

    .badge {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 999px;
        background: #eaf6ee;
        margin: 4px;
        font-size: 0.85rem;
    }

    .study-meta {
        direction: rtl !important;
        text-align: right !important;
        color: #5d6c63;
        font-size: 0.94rem;
        font-weight: 700;
        margin: 8px 0 18px 0;
    }

    .researcher-title {
        background: linear-gradient(135deg, #ffffff 0%, #e9f7ee 100%);
        border: 1px solid #d7eadf;
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 20px;
        direction: rtl;
        text-align: right;
    }

    .researcher-note {
        color: #5f7066;
        line-height: 2;
    }

    [data-testid="stForm"], [data-testid="stTabs"], .stDataFrame {
        direction: rtl !important;
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
if not MODEL_PATH.exists():
    MODEL_PATH = Path("random_forest_pipeline.joblib")

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


def _normalize_model_class(value, classes=None):
    """Normalize model labels using the actual class coding used by the saved model."""
    text = ("" if value is None else str(value)).strip().lower()

    direct = {
        "low": "low", "medium": "medium", "high": "high",
        "پایین": "low", "متوسط": "medium", "بالا": "high",
    }
    if text in direct:
        return direct[text]

    try:
        n = int(float(text))
    except Exception:
        return text

    # Common 3-class encodings: 0/1/2 or 1/2/3.
    numeric_classes = []
    if classes is not None:
        for cls in classes:
            try:
                numeric_classes.append(int(float(str(cls))))
            except Exception:
                numeric_classes = []
                break

    if len(numeric_classes) == 3:
        ordered = sorted(set(numeric_classes))
        if ordered == [0, 1, 2]:
            return {0: "low", 1: "medium", 2: "high"}[n]
        if ordered == [1, 2, 3]:
            return {1: "low", 2: "medium", 3: "high"}[n]

    # Fallback only when the common zero-based encoding is clearly implied.
    if n in (0, 1, 2):
        return {0: "low", 1: "medium", 2: "high"}[n]

    return text


def build_model_input(student_data):
    """
    Build input for the deployed 7-feature Random Forest pipeline.

    The deployed pipeline was trained with:
      numeric: Age_Num, ترمتحصیلی
      categorical: جنسیت, مقطع, استفاده, دانشگاه, رشتهتحصیلی

    Therefore categorical values must be passed in their original textual
    form; converting them to numeric codes changes the feature representation
    expected by the fitted preprocessing pipeline and can cause prediction
    failures.
    """
    age = student_data.get("age")
    semester = student_data.get("semester")
    gender = str(student_data.get("gender", "")).strip()
    degree = str(student_data.get("degree", "")).strip()
    daily_use = str(student_data.get("daily_use", "")).strip()
    university = str(student_data.get("university", "")).strip()
    major = str(student_data.get("major", "")).strip()

    if age in (None, "") or semester in (None, ""):
        raise ValueError("سن و ترم تحصیلی برای اجرای مدل لازم است.")

    required_categories = {
        "جنسیت": gender,
        "مقطع": degree,
        "استفاده": daily_use,
        "دانشگاه": university,
        "رشتهتحصیلی": major,
    }
    missing = [name for name, value in required_categories.items() if not value]
    if missing:
        raise ValueError("برخی ویژگی‌های ورودی مدل خالی هستند: " + ", ".join(missing))

    return pd.DataFrame([{
        "Age_Num": int(age),
        "جنسیت": gender,
        "مقطع": degree,
        "ترمتحصیلی": int(semester),
        "استفاده": daily_use,
        "دانشگاه": university,
        "رشتهتحصیلی": major,
    }])


def predict_level(student_data):
    """Return a validated model estimate plus probabilities."""
    model = get_model()
    if model is None:
        return {
            "level": None,
            "raw_prediction": "",
            "probabilities": {},
            "error": "فایل مدل پیدا نشد.",
        }

    try:
        x = build_model_input(student_data)
        raw_prediction = model.predict(x)[0]
        classes = list(getattr(model, "classes_", []))
        prediction = _normalize_model_class(raw_prediction, classes=classes)

        probabilities = {}
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(x)[0]
            for cls, prob in zip(classes, proba):
                label = _normalize_model_class(cls, classes=classes)
                probabilities[label] = float(prob)

        if prediction not in {"low", "medium", "high"}:
            # اگر مدل خروجی فارسی یا کد غیر استاندارد داد، آن را متوقف نکن
            fallback = _normalize_model_class(raw_prediction, classes=classes)
            if fallback in {"low", "medium", "high"}:
                prediction = fallback
            else:
                return {
                    "level": None,
                    "raw_prediction": str(raw_prediction),
                    "probabilities": probabilities,
                    "error": (
                        "خروجی مدل نامشخص بود؛ در ادامه از سطح پرسشنامه استفاده شد."
                    ),
                }

        return {
            "level": prediction,
            "raw_prediction": str(raw_prediction),
            "probabilities": probabilities,
            "classes": [str(c) for c in classes],
        }
    except Exception as exc:
        # در صورت خطای واقعی مدل (مثلاً ناسازگاری دسته‌ها با pipeline آموزش‌دیده)
        # به‌جای تحمیل «متوسط»، مقدار None برگردانده می‌شود تا در ادامه
        # از سطح پرسشنامه استفاده شود.
        return {
            "level": None,
            "raw_prediction": "",
            "probabilities": {},
            "error": f"{type(exc).__name__}: {exc}",
        }


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


def row_to_intervention(row):
    """Convert a study_interventions DB row into the minimal intervention object."""
    return {
        "day_number": row[2],
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
    # نام‌های نمایشی برای رابط دانشجو؛ نام داخلی پروفایل فقط در لایه پژوهش/منطق باقی می‌ماند.
    focus_names = {
        "task_initiation": "شروع به‌موقع فعالیت",
        "educational_content": "مطالعه مرحله‌ای محتوای عقب‌افتاده",
        "deadline_time": "مدیریت زمان و مهلت‌ها",
        "participation": "فعال‌تر کردن حضور و مشارکت",
        "task_difficulty": "شروع و پیشروی در تکلیف دشوار",
        "digital_distraction": "مدیریت حواس‌پرتی دیجیتال",
        "help_seeking": "فعال‌تر کردن کمک‌خواهی",
        "group_activity": "پیشبرد به‌موقع فعالیت گروهی",
        "stress_guilt": "مدیریت فشار و احساس گناه",
        "general_procrastination": "پیشروی به‌موقع در کارهای تحصیلی",
    }

    raw_name = str(intervention.get("name", "برنامه پیشنهادی")).replace("مداخله", "برنامه")
    profile_key = str(intervention.get("profile", ""))
    base_focus = focus_names.get(profile_key, raw_name)
    day_number = intervention.get("day_number")
    stage_title = ""
    if day_number is not None:
        try:
            stage_title = _daily_stage_templates(profile_key).get(int(day_number), {}).get("title", "")
        except Exception:
            stage_title = ""
    display_title = base_focus
    if stage_title:
        display_title = f"{base_focus} — {stage_title}"
    name = html.escape(display_title)
    description = html.escape(
        str(intervention.get("description", ""))
        .replace("برنامه خردشده محتوای انباشته", "مطالعه مرحله‌ای محتوای عقب‌افتاده")
        .replace("مداخله", "برنامه")
    )

    st.markdown(
        f"""
        <div class="intervention">
            <div class="intervention-title">
                تمرکز امروز: {name}
            </div>
            <p>{description}</p>
        """,
        unsafe_allow_html=True,
    )

    for action in intervention.get("actions") or []:
        safe_action = html.escape(str(action))
        st.markdown(
            f'<div class="action">✓ {safe_action}</div>',
            unsafe_allow_html=True,
        )

    presentation = intervention.get("presentation") or {}
    notes = [
        presentation.get("detail_note"),
        presentation.get("time_note"),
    ]
    notes = [x for x in notes if x]

    if notes:
        safe_notes = html.escape(" ".join(str(x) for x in notes))
        st.markdown(
            f'<div class="small">نحوه ارائه: {safe_notes}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


def render_student_context(student):
    age = html.escape(str(to_persian_digits(student["age"])))
    gender = html.escape(str(student["gender"]))
    degree = html.escape(str(student["degree"]))
    semester = html.escape(str(to_persian_digits(student["semester"])))
    daily_use = html.escape(str(student["daily_use"]))
    university = html.escape(str(student["university"]))
    major = html.escape(str(student["major"]))
    st.markdown(
        f"""
        <div class="card">
            <span class="badge">سن: {age}</span>
            <span class="badge">جنسیت: {gender}</span>
            <span class="badge">مقطع: {degree}</span>
            <span class="badge">ترم: {semester}</span>
            <span class="badge">استفاده روزانه: {daily_use}</span>
            <span class="badge">دانشگاه: {university}</span>
            <span class="badge">رشته: {major}</span>
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
                f"{to_persian_digits(i)}. {question}",
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


def calculate_intervention_result(student, answers):
    # Keep only the 22 questionnaire items. Database metadata such as
    # assessment_id must never enter profile calculation or AI context.
    questionnaire_answers = {
        f"q{i}": int(answers[f"q{i}"])
        for i in range(1, 23)
        if f"q{i}" in answers
    }
    if len(questionnaire_answers) != 22:
        raise ValueError("پاسخ‌های پرسشنامه باید شامل دقیقاً 22 سؤال q1 تا q22 باشند.")

    total_score = calculate_total_score(questionnaire_answers)
    overall_level = classify_overall_level(total_score)

    profile_result = create_profile(questionnaire_answers)

    ml_result = predict_level(student)
    estimated_level = (
        ml_result.get("level")
        if isinstance(ml_result, dict)
        and ml_result.get("level") in {"low", "medium", "high"}
        else overall_level
    )

    # The behavioral profile determines the intervention type. The questionnaire
    # level remains available for decision-making; the ML estimate can increase
    # intensity only when it is a validated three-level output.
    level_rank = {"low": 0, "medium": 1, "high": 2}
    ml_rank = level_rank.get(estimated_level, -1)
    decision_level = (
        max(overall_level, key=lambda x: level_rank.get(x, 0))
        if ml_rank < 0
        else (
            overall_level
            if level_rank.get(overall_level, 0) >= ml_rank
            else estimated_level
        )
    )

    decision = choose_intervention(
        questionnaire_answers,
        overall_level=decision_level,
        profile_result=profile_result,
    )

    interventions = [
        personalize_presentation(item, student)
        for item in decision.get("interventions", [])
    ]

    primary = interventions[0] if interventions else None

    return {
        "answers": questionnaire_answers,
        "total_score": total_score,
        "overall_level": overall_level,
        "profile_result": profile_result,
        "ml_result": ml_result,
        "estimated_level": estimated_level,
        "decision_level": decision_level,
        "interventions": interventions,
        "primary": primary,
    }


@st.cache_data(show_spinner=False)
def calculate_intervention_result_cached(student_items, answer_items):
    student = dict(student_items)
    answers = dict(answer_items)
    return calculate_intervention_result(student, answers)


def _student_cache_items(student):
    return tuple(sorted((str(k), str(v)) for k, v in (student or {}).items()))


def _answer_cache_items(answers):
    return tuple(sorted((str(k), int(v)) for k, v in (answers or {}).items() if str(k).lower().startswith("q") and str(k)[1:].isdigit()))


def save_pretest(student, answers):
    result = calculate_intervention_result_cached(_student_cache_items(student), _answer_cache_items(answers))

    assessment_id = save_assessment_with_responses(
        student["student_code"],
        "pretest",
        result["total_score"],
        result["overall_level"],
        answers,
    )

    return result, assessment_id


def save_posttest(student, answers):
    result = calculate_intervention_result_cached(_student_cache_items(student), _answer_cache_items(answers))

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


def _daily_stage_templates(profile_key):
    """Seven progressive execution stages while keeping the behavioral focus stable."""
    return {
        1: {"title": "شروع کوچک", "suffix": "امروز فقط کوچک‌ترین گام اجرایی برنامه را شروع کن.", "actions": ["یک گام بسیار کوچک از برنامه را انتخاب کن.", "زمان شروع را همین حالا مشخص کن."]},
        2: {"title": "تداوم شروع", "suffix": "امروز همان مسیر را در یک بازه کوتاه ادامه بده.", "actions": ["همان فعالیت را در یک بازه کوتاه ادامه بده.", "بعد از پایان بازه، پیشرفت انجام‌شده را ثبت کن."]},
        3: {"title": "کاهش اصطکاک", "suffix": "امروز یک مانع اصلی اجرای برنامه را پیش از شروع کمتر کن.", "actions": ["یک عامل مزاحم یا دشوار را پیش از شروع حذف کن.", "فعالیت را به یک گام روشن و قابل اجرا تبدیل کن."]},
        4: {"title": "اجرای هدفمند", "suffix": "امروز یک بازه مشخص و قابل اجرا را کامل کن.", "actions": ["یک بازه مشخص برای اجرای برنامه تعیین کن.", "تا پایان همان بازه روی فعالیت امروز بمان."]},
        5: {"title": "پیشروی مستقل", "suffix": "امروز بخشی از کار را با وابستگی کمتر به یادآوری بیرونی پیش ببر.", "actions": ["شروع را به یک نشانه مشخص در برنامه روزانه وصل کن.", "بخش بعدی را بدون تعویق طولانی ادامه بده."]},
        6: {"title": "تثبیت", "suffix": "امروز راهبردی را که بهتر جواب داده تکرار و تثبیت کن.", "actions": ["بهترین راهبرد روزهای قبل را تکرار کن.", "مانع تکرارشونده را کوتاه یادداشت کن."]},
        7: {"title": "جمع‌بندی و انتقال", "suffix": "امروز الگوی مؤثر این هفته را برای ادامه مسیر حفظ کن.", "actions": ["یک رفتار مؤثر این هفته را مشخص کن.", "همان رفتار را به برنامه روزهای بعد منتقل کن."]},
    }


def build_daily_intervention(base_intervention, day_number, previous_log=None):
    """Create a day-specific progression based on day and prior-day execution."""
    item = dict(base_intervention)
    stage = _daily_stage_templates(item.get("profile", "")).get(int(day_number), {})
    base_name = str(item.get("name", "برنامه پیشنهادی")).strip()
    base_desc = str(item.get("description", "")).strip()
    item["name"] = f"{base_name} — {stage.get('title', f'روز {day_number}')}"
    item["description"] = f"{base_desc} {stage.get('suffix', '')}".strip()
    item["actions"] = list(stage.get("actions", [])) + (item.get("actions") or [])[:1]

    prev_status = previous_log[3] if previous_log and len(previous_log) > 3 else None
    if prev_status == "not_started":
        item["description"] += " با توجه به اینکه فعالیت روز قبل شروع نشد، امروز نقطه شروع را کوچک‌تر و فوری نگه دار."
        item["actions"].insert(0, "فقط ۵ تا ۱۰ دقیقه اول فعالیت را متعهد شو.")
    elif prev_status == "partial":
        item["description"] += " با توجه به اجرای ناقص روز قبل، امروز از همان بخش باقی‌مانده ادامه بده."
        item["actions"].insert(0, "از همان بخش ناتمام روز قبل ادامه بده.")
    elif prev_status == "completed":
        item["description"] += " با توجه به اجرای کامل روز قبل، امروز همان الگوی موفق را یک مرحله جلوتر ببر."

    return item


def ensure_daily_interventions(student, study_day, base_result):
    """Get or create the requested day's intervention snapshot exactly once."""
    student_code = student["student_code"]
    existing = get_study_interventions(student_code, day_number=study_day)
    if existing:
        return existing

    previous_log = None
    if int(study_day) > 1:
        previous_log = get_daily_log(student_code, int(study_day) - 1)

    daily_items = [
        build_daily_intervention(item, study_day, previous_log)
        for item in (base_result.get("interventions") or [])[:2]
    ]

    for index, intervention in enumerate(daily_items, start=1):
        save_study_intervention(
            student_code=student_code,
            day_number=int(study_day),
            profile=intervention.get("profile", ""),
            profile_score=intervention.get("profile_score"),
            profile_level=intervention.get("profile_level", ""),
            overall_level=base_result.get("overall_level", ""),
            estimated_level=base_result.get("estimated_level", ""),
            intervention_name=intervention.get("name", ""),
            intervention_description=intervention.get("description", ""),
            intensity=intervention.get("intensity", "medium"),
            intervention_order=index,
        )

    return get_study_interventions(student_code, day_number=int(study_day))


def render_result_summary(result):
    c1, c2, c3 = st.columns(3)
    total_text = to_persian_digits(f"{result['total_score']:.1f}")
    c1.metric("نمره کل", f"{total_text} از {to_persian_digits(110)}")
    c2.metric("سطح پرسشنامه", LEVEL_NAMES.get(result["overall_level"], result["overall_level"]))
    estimated_display = LEVEL_NAMES.get(
        result.get("estimated_level"),
        "نامشخص" if result.get("estimated_level") == "unknown" else str(result.get("estimated_level", "")),
    )
    c3.metric("برآورد مدل", estimated_display)

    ml = result.get("ml_result")
    if ml and ml.get("error"):
        st.warning(f"برآورد مدل در این اجرا انجام نشد: {ml['error']}")
    if ml and ml.get("probabilities"):
        p = ml["probabilities"]
        st.caption(
            "احتمال‌های مدل: "
            + " | ".join(
                f"{LEVEL_NAMES.get(k, k)}: {to_persian_digits(f'{v:.1%}')}"
                for k, v in p.items()
            )
        )


def build_today_monitoring(today_log):
    """Convert the persisted daily log into a safe context for the AI coach."""
    if not today_log:
        return {
            "status": "not_started",
            "minutes": None,
            "notes": "",
            "checkin_question": "",
            "checkin_answer": "",
        }

    return {
        "status": today_log[3] if len(today_log) > 3 else "not_started",
        "minutes": today_log[4] if len(today_log) > 4 else None,
        "notes": today_log[6] if len(today_log) > 6 else "",
        "checkin_question": today_log[8] if len(today_log) > 8 else "",
        "checkin_answer": today_log[9] if len(today_log) > 9 else "",
    }


def get_daily_checkin_question(profile, day_number):
    """Return one concise daily process-monitoring question.

    The wording changes by day and dominant behavioral profile. Responses are
    process data only and are not added to the 22-item procrastination score.
    """
    question_bank = {
        "task_initiation": [
            "امروز شروع فعالیت برایت تا چه اندازه دشوار بود؟",
            "امروز تا چه اندازه توانستی فعالیت را بدون تأخیر طولانی شروع کنی؟",
            "امروز تا چه اندازه تصمیم برای شروع به شروع واقعی کار تبدیل شد؟",
            "امروز تا چه اندازه شروع فعالیت برایت سریع‌تر از معمول انجام شد؟",
            "امروز تا چه اندازه توانستی مانع شروع کار را پشت سر بگذاری؟",
            "امروز تا چه اندازه از راهبرد شروع کوتاه برای آغاز کار استفاده کردی؟",
        ],
        "educational_content": [
            "امروز تا چه اندازه محتوای آموزشی برنامه‌ریزی‌شده را مطالعه کردی؟",
            "امروز تا چه اندازه مطالعه محتوای آموزشی را به‌موقع شروع کردی؟",
            "امروز تا چه اندازه توانستی مطالعه محتوای آموزشی را ادامه بدهی؟",
            "امروز تا چه اندازه مطالعه محتوا را از زمان برنامه‌ریزی‌شده عقب انداختی؟",
            "امروز تا چه اندازه نسبت به روز قبل در مطالعه محتوا پیشرفت داشتی؟",
            "امروز تا چه اندازه توانستی محتوای آموزشی را به بخش‌های کوچک‌تر تقسیم کنی؟",
        ],
        "deadline_time": [
            "امروز تا چه اندازه طبق زمان‌بندی تعیین‌شده پیش رفتی؟",
            "امروز تا چه اندازه فعالیت را قبل از نزدیک‌شدن به مهلت انجام دادی؟",
            "امروز تا چه اندازه توانستی زمان فعالیت را مدیریت کنی؟",
            "امروز تا چه اندازه کار را به دقایق پایانی موکول کردی؟",
            "امروز تا چه اندازه نسبت به روز قبل کنترل بیشتری بر زمان داشتی؟",
            "امروز تا چه اندازه توانستی برای فعالیت زمان مشخص و قابل اجرا تعیین کنی؟",
        ],
        "participation": [
            "امروز تا چه اندازه در فعالیت یا مشارکت آموزشی برنامه‌ریزی‌شده حضور داشتی؟",
            "امروز تا چه اندازه مشارکت در فعالیت آنلاین برایت آسان بود؟",
            "امروز تا چه اندازه توانستی به‌موقع در فعالیت آموزشی مشارکت کنی؟",
            "امروز تا چه اندازه مشارکت آموزشی را به زمان دیگری موکول کردی؟",
            "امروز تا چه اندازه نسبت به روز قبل در مشارکت پیشرفت داشتی؟",
            "امروز تا چه اندازه برای مشارکت آنلاین آمادگی داشتی؟",
        ],
        "task_difficulty": [
            "امروز تا چه اندازه دشواری تکلیف شروع یا ادامه آن را سخت کرد؟",
            "امروز تا چه اندازه توانستی با بخش دشوار تکلیف ادامه بدهی؟",
            "امروز تا چه اندازه دشواری تکلیف روی پیشروی تو اثر گذاشت؟",
            "امروز تا چه اندازه به دلیل دشواری، انجام تکلیف را عقب انداختی؟",
            "امروز تا چه اندازه نسبت به روز قبل در مواجهه با دشواری بهتر عمل کردی؟",
            "امروز تا چه اندازه توانستی بخش دشوار تکلیف را به گام‌های کوچک‌تر تبدیل کنی؟",
        ],
        "digital_distraction": [
            "امروز تا چه اندازه حواس‌پرتی دیجیتال هنگام فعالیت برایت مشکل ایجاد کرد؟",
            "امروز تا چه اندازه توانستی عوامل حواس‌پرت‌کن دیجیتال را کنترل کنی؟",
            "امروز تا چه اندازه هنگام فعالیت سراغ شبکه‌های اجتماعی یا وبگردی رفتی؟",
            "امروز تا چه اندازه توانستی یک بازه بدون حواس‌پرتی دیجیتال ایجاد کنی؟",
            "امروز تا چه اندازه حواس‌پرتی دیجیتال نسبت به روز قبل کمتر بود؟",
            "امروز تا چه اندازه از راهبرد تمرکز دیجیتال استفاده کردی؟",
        ],
        "help_seeking": [
            "امروز تا چه اندازه برای ابهام یا مشکل درسی به‌موقع کمک خواستی؟",
            "امروز تا چه اندازه درخواست کمک از استاد یا منبع آموزشی برایت آسان بود؟",
            "امروز تا چه اندازه توانستی بدون تعلل برای مشکل درسی اقدام کنی؟",
            "امروز تا چه اندازه کمک‌خواهی را به زمان دیگری موکول کردی؟",
            "امروز تا چه اندازه نسبت به روز قبل در کمک‌خواهی به‌موقع‌تر بودی؟",
            "امروز تا چه اندازه از راهبرد کمک‌خواهی استفاده کردی؟",
        ],
        "group_activity": [
            "امروز تا چه اندازه سهم خودت از فعالیت گروهی را طبق برنامه انجام دادی؟",
            "امروز تا چه اندازه هماهنگی با همگروهی‌ها برایت آسان بود؟",
            "امروز تا چه اندازه توانستی سهم خود را به‌موقع پیش ببری؟",
            "امروز تا چه اندازه مسئولیت گروهی را عقب انداختی؟",
            "امروز تا چه اندازه نسبت به روز قبل در فعالیت گروهی پیشرفت داشتی؟",
            "امروز تا چه اندازه برای تحویل به‌موقع سهم گروهی برنامه داشتی؟",
        ],
        "stress_guilt": [
            "امروز تا چه اندازه هنگام عقب‌افتادن از برنامه احساس فشار کردی؟",
            "امروز تا چه اندازه توانستی فشار ذهنی هنگام انجام فعالیت را مدیریت کنی؟",
            "امروز تا چه اندازه احساس گناه روی انجام فعالیت اثر گذاشت؟",
            "امروز تا چه اندازه فشار ذهنی باعث تعویق فعالیت شد؟",
            "امروز تا چه اندازه احساس فشار نسبت به روز قبل کمتر بود؟",
            "امروز تا چه اندازه از یک راهبرد آرام‌سازی یا شروع مرحله‌ای استفاده کردی؟",
        ],
        "general_procrastination": [
            "امروز تا چه اندازه توانستی کارهای تحصیلی را به‌موقع انجام دهی؟",
            "امروز تا چه اندازه شروع کارهای تحصیلی برایت آسان بود؟",
            "امروز تا چه اندازه توانستی در برابر تعویق مقاومت کنی؟",
            "امروز تا چه اندازه بخشی از کارها را بیشتر از برنامه عقب انداختی؟",
            "امروز تا چه اندازه نسبت به روز قبل در به‌موقع انجام‌دادن کارها پیشرفت داشتی؟",
            "امروز تا چه اندازه از راهبرد تعیین یک گام کوچک برای پیشروی استفاده کردی؟",
        ],
    }

    questions = question_bank.get(profile) or question_bank["general_procrastination"]
    index = max(0, min(int(day_number) - 1, len(questions) - 1))
    return questions[index]


# ============================================================
# Researcher-only page
# ============================================================

GROUP_LABELS = {
    "intervention": "گروه پشتیبانی",
    "control": "گروه روال معمول",
}


def _jalali_created(value):
    if not value:
        return ""
    try:
        return jalali_from_gregorian(date.fromisoformat(str(value)[:10]))
    except Exception:
        return ""


def _researcher_dataframes():
    conn = get_connection()
    try:
        participants = pd.read_sql_query("SELECT student_code, group_type, start_date, end_date, status, consent, created_at FROM study_participants ORDER BY id", conn)
        students = pd.read_sql_query("SELECT * FROM students ORDER BY id", conn)
        assessments = pd.read_sql_query("SELECT id, student_code, assessment_type, total_score, level, created_at FROM assessments ORDER BY id", conn)
        responses = pd.read_sql_query("SELECT * FROM assessment_responses ORDER BY id", conn)
        programs = pd.read_sql_query("SELECT id, student_code, day_number, intervention_order, profile, profile_score, profile_level, overall_level, estimated_level, intervention_name, intervention_description, intensity, shown_at FROM study_interventions ORDER BY id", conn)
        daily = pd.read_sql_query("SELECT * FROM daily_logs ORDER BY id", conn)
        coach = pd.read_sql_query("SELECT * FROM coach_logs ORDER BY id", conn)
    finally:
        conn.close()

    if not participants.empty:
        participants["گروه"] = participants["group_type"].map(GROUP_LABELS).fillna("")
        participants["تاریخ شروع"] = participants["start_date"].fillna("").map(to_persian_digits)
        participants["تاریخ پایان"] = participants["end_date"].fillna("").map(to_persian_digits)
        participants["رضایت"] = participants["consent"].map({1: "ثبت شده", 0: "ثبت نشده"}).fillna("")
        participants["تاریخ ثبت شمسی"] = participants["created_at"].map(_jalali_created)
        participants = participants.drop(columns=["group_type"], errors="ignore")

    if not students.empty:
        students = students.rename(columns={
            "student_code": "کد پژوهشی", "age": "سن", "gender": "جنسیت",
            "degree": "مقطع", "semester": "ترم", "use_level": "استفاده روزانه",
            "university": "دانشگاه", "major": "رشته",
            "registered_at_jalali": "تاریخ ثبت اطلاعات",
        })
        if "تاریخ ثبت اطلاعات" in students.columns:
            students["تاریخ ثبت اطلاعات"] = students["تاریخ ثبت اطلاعات"].fillna("").map(to_persian_digits)

    if not assessments.empty:
        assessments["نوع آزمون"] = assessments["assessment_type"].map({"pretest": "پیش‌آزمون", "posttest": "پس‌آزمون"}).fillna(assessments["assessment_type"])
        assessments["تاریخ شمسی"] = assessments["created_at"].map(_jalali_created)

    if not responses.empty and not assessments.empty and "assessment_id" in responses.columns:
        response_dates = assessments[["id", "تاریخ شمسی"]].rename(columns={"id": "assessment_id"})
        responses = responses.merge(response_dates, on="assessment_id", how="left")

    if not coach.empty and "created_at" in coach.columns:
        coach["تاریخ شمسی"] = coach["created_at"].map(_jalali_created)

    if not daily.empty:
        start_map = participants.set_index("student_code")["start_date"].to_dict() if not participants.empty else {}
        def row_date(row):
            start = start_map.get(row["student_code"])
            try:
                g = jalali_to_gregorian(*[int(x) for x in str(start).split("/")[:3]])
                return jalali_from_gregorian(g + pd.Timedelta(days=int(row["day_number"]) - 1))
            except Exception:
                return ""
        daily["تاریخ شمسی"] = daily.apply(row_date, axis=1)
        daily["وضعیت"] = daily["action_status"].map({
            "not_started": "هنوز شروع نکردم",
            "partial": "بخشی از آن را انجام دادم",
            "completed": "کامل انجام دادم",
        }).fillna(daily["action_status"])

    if not programs.empty:
        programs["تاریخ شمسی"] = programs["shown_at"].map(_jalali_created)

    for frame in (students, assessments, responses, programs, daily, coach):
        for col in frame.columns:
            if frame[col].dtype == "object":
                frame[col] = frame[col].map(lambda x: str(x).replace("مداخله", "برنامه") if pd.notna(x) else x)

    return {
        "شرکت‌کنندگان": participants,
        "اطلاعات دانشجو": students,
        "آزمون‌ها": assessments,
        "پاسخ‌های ۲۲ سؤال": responses,
        "برنامه‌های ثبت‌شده": programs,
        "پایش روزانه": daily,
        "مربی هوشمند": coach,
    }


def _make_excel(dataframes):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet, df in dataframes.items():
            df.to_excel(writer, sheet_name=sheet[:31], index=False)
    return output.getvalue()


def render_researcher_page():
    st.markdown(
        """
        <div class="researcher-title">
            <h1>صفحه پژوهشگر</h1>
            <div class="researcher-note">این صفحه فقط با کد پژوهشگر قابل دسترسی است و در مسیر معمول شرکت‌کننده نمایش داده نمی‌شود.</div>
        </div>
        """, unsafe_allow_html=True
    )

    if not st.session_state.get("researcher_authenticated", False):
        with st.form("researcher_login"):
            code = st.text_input("کد پژوهشگر", type="password")
            submitted = st.form_submit_button("ثبت و بررسی", type="primary", use_container_width=True)

        if submitted:
            if not code.strip():
                st.error("کد پژوهشگر را وارد کنید.")
            else:
                try:
                    researcher = verify_researcher_code(code.strip())
                except Exception as exc:
                    researcher = None
                    st.error(f"خطا در بررسی کد: {exc}")

                if researcher:
                    st.session_state.researcher_authenticated = True
                    st.session_state.researcher_role = researcher.get("role", "researcher")
                    st.rerun()
                else:
                    st.error("کد پژوهشگر نادرست است.")
        return

    st.success("دسترسی پژوهشگر تأیید شد.")
    col_a, col_b = st.columns([1, 4])
    with col_a:
        if st.button("خروج پژوهشگر", use_container_width=True):
            st.session_state.researcher_authenticated = False
            st.session_state.researcher_role = "researcher"
            st.rerun()
    with col_b:
        st.caption("آخرین داده‌های ثبت‌شده از سامانه")

    st.info("روز مطالعه هر شرکت‌کننده به‌صورت خودکار بر اساس تاریخ شروع مطالعه محاسبه می‌شود.")

    st.subheader("ثبت شرکت‌کننده")
    with st.form("researcher_register"):
        code = st.text_input("کد پژوهشی", placeholder="مثلاً P101").strip().upper()
        group = st.selectbox("گروه", ["intervention", "control"], format_func=lambda x: GROUP_LABELS[x])
        register = st.form_submit_button("ثبت و بررسی", type="primary", use_container_width=True)
    if register:
        if not code:
            st.error("کد پژوهشی را وارد کنید.")
        else:
            try:
                register_study_participant(student_code=code, group_type=group, consent=False, status="active")
                p = get_study_participant(code)
                st.success(f"کد {code} در {GROUP_LABELS[group]} ثبت شد.")
                if p:
                    st.info(f"تاریخ شروع: {to_persian_digits(p.get('start_date', ''))} | وضعیت: {p.get('status', '')}")
            except Exception as exc:
                st.error(f"ثبت شرکت‌کننده انجام نشد: {exc}")

    dataframes = _researcher_dataframes()
    participants = dataframes["شرکت‌کنندگان"]
    assessments = dataframes["آزمون‌ها"]
    daily = dataframes["پایش روزانه"]

    # Concise participant-level summary for the researcher.
    summary = participants[[c for c in ["student_code", "گروه", "تاریخ شروع", "تاریخ پایان", "status"] if c in participants.columns]].copy()
    if not summary.empty:
        summary = summary.rename(columns={"student_code": "کد پژوهشی", "status": "وضعیت"})
        if not assessments.empty:
            for kind, label in [("pretest", "نمره پیش‌آزمون"), ("posttest", "نمره پس‌آزمون")]:
                sub = assessments.loc[assessments["assessment_type"] == kind, ["student_code", "total_score"]].copy()
                if not sub.empty:
                    sub = sub.sort_values("student_code").drop_duplicates("student_code", keep="last")
                    sub[label] = sub["total_score"].map(lambda x: round(float(x), 1))
                    summary = summary.merge(sub[["student_code", label]], left_on="کد پژوهشی", right_on="student_code", how="left").drop(columns=["student_code"])
        if "نمره پیش‌آزمون" in summary.columns and "نمره پس‌آزمون" in summary.columns:
            summary["تغییر نمره"] = summary["نمره پس‌آزمون"] - summary["نمره پیش‌آزمون"]

    st.divider()
    st.subheader("نتایج ثبت‌شده")
    m1, m2, m3 = st.columns(3)
    m1.metric("شرکت‌کنندگان", to_persian_digits(len(participants)))
    m2.metric("آزمون‌ها", to_persian_digits(len(assessments)))
    m3.metric("گزارش‌های روزانه", to_persian_digits(len(daily)))

    if not summary.empty:
        st.markdown("### خلاصه نتایج هر شرکت‌کننده")
        summary_view = summary.copy()
        for col in ["نمره پیش‌آزمون", "نمره پس‌آزمون", "تغییر نمره"]:
            if col in summary_view.columns:
                summary_view[col] = summary_view[col].map(lambda x: to_persian_digits(round(float(x), 1)) if pd.notna(x) else "")
        st.dataframe(summary_view, use_container_width=True, hide_index=True)

    if participants.empty:
        st.info("هنوز شرکت‌کننده‌ای ثبت نشده است.")
    else:
        show_cols = ["student_code", "گروه", "تاریخ شروع", "تاریخ پایان", "status", "رضایت", "تاریخ ثبت شمسی"]
        view = participants[[c for c in show_cols if c in participants.columns]].rename(columns={"student_code": "کد پژوهشی", "status": "وضعیت"})
        st.dataframe(view, use_container_width=True, hide_index=True)

    tabs = st.tabs(list(dataframes.keys()))
    for tab, (name, df) in zip(tabs, dataframes.items()):
        with tab:
            st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("خروجی پژوهش")
    excel = _make_excel(dataframes)
    st.download_button(
        "دانلود نتایج به صورت Excel",
        data=excel,
        file_name="research_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )


if str(st.query_params.get("page", "")).strip().lower() == "researcher":
    # Researcher authentication state is initialized before this branch.
    if "researcher_authenticated" not in st.session_state:
        st.session_state.researcher_authenticated = False
    if "researcher_role" not in st.session_state:
        st.session_state.researcher_role = "researcher"
    render_researcher_page()
    st.stop()

# ============================================================
# Session initialization
# ============================================================

for key, default in {
    "student_code": "",
    "student": None,
    "participant": None,
    "pending_participant_code": "",
    "pending_participant": None,
    "researcher_authenticated": False,
    "researcher_role": "researcher",
    "consent_saved": False,
    "day_ended": None,
    "posttest_saved": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


def set_study_consent(student_code, consent=True):
    """Persist participant consent using PostgreSQL syntax."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE study_participants SET consent = %s WHERE student_code = %s",
                (1 if consent else 0, student_code),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def render_consent_page(code, participant):
    """Show informed consent before the participant enters the study."""
    st.subheader("رضایت آگاهانه برای شرکت در مطالعه")
    st.markdown(
        """
        <div class="card">
            <h3>اطلاعات مطالعه</h3>
            <p>
            این سامانه بخشی از یک پژوهش دانشگاهی درباره اهمال‌کاری تحصیلی
            در آموزش الکترونیکی است.
            </p>
            <p>
            در صورت موافقت، ابتدا اطلاعات جمعیت‌شناختی و آموزشی و یک پرسشنامه
            ۲۲ سؤالی تکمیل می‌کنید و سپس در یک دوره ۷ روزه در مطالعه شرکت
            می‌کنید. در پایان، همان پرسشنامه برای بار دوم اجرا می‌شود.
            </p>
            <p>
            شرکت در این پژوهش داوطلبانه است و می‌توانید در هر زمان بدون پیامد آموزشی
            از ادامه همکاری منصرف شوید. داده‌ها با کد پژوهشی ذخیره و برای اهداف پژوهشی
            استفاده می‌شوند.
            </p>
            <p>
            سامانه یک ابزار پژوهشی و تصمیم‌یار آموزشی است و تشخیص پزشکی یا
            روان‌شناختی ارائه نمی‌کند.
            </p>
            <p>
            پرسشنامه حاضر با بهره‌گیری از مبانی نظری و مؤلفه‌های پرسشنامه
            اهمال‌کاری تحصیلی Solomon and Rothblum تدوین شده و گویه‌های آن با
            توجه به ویژگی‌ها و الزامات بستر آموزش الکترونیکی بازنگری،
            متناسب‌سازی و بهینه‌سازی شده است.
            </p>
            <p class="small">
            <b>اطلاعات تماس پژوهشگر:</b> mohadesealiakbarloo@gmail.com
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form(f"consent_form_{code}"):
        agreed = st.checkbox(
            "مطالب بالا را مطالعه کردم و با شرکت داوطلبانه در مطالعه موافقم.",
            key=f"consent_checkbox_{code}",
        )
        submitted = st.form_submit_button(
            "تأیید رضایت و ادامه",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if not agreed:
            st.error("برای ادامه مطالعه، تأیید رضایت آگاهانه لازم است.")
            return

        try:
            set_study_consent(code, True)
            updated = get_study_participant(code) or participant
            st.session_state.pending_participant_code = code
            st.session_state.pending_participant = updated
            st.session_state.consent_saved = True
            st.rerun()
        except Exception as exc:
            st.error(f"ثبت رضایت انجام نشد: {exc}")


def render_participant_info_form(code, participant):
    """Collect and persist the seven demographic/educational model inputs."""
    st.subheader("تکمیل اطلاعات شرکت‌کننده")
    st.caption(
        "این اطلاعات برای اجرای مدل و شخصی‌سازی نحوه ارائه برنامه "
        "ثبت می‌شوند. کد پژوهشی ناشناس باقی می‌ماند."
    )

    with st.form("participant_info_form"):
        c1, c2 = st.columns(2)
        with c1:
            age_raw = st.text_input("سن", placeholder="مثلاً ۲۰")
            gender = st.selectbox("جنسیت", ["زن", "مرد"])
            degree = st.selectbox("مقطع تحصیلی", ["کارشناسی", "کارشناسی ارشد", "دکتری"])
            semester_raw = st.text_input("ترم تحصیلی", placeholder="مثلاً ۴")
        with c2:
            daily_use = st.selectbox(
                "میزان استفاده روزانه از آموزش الکترونیکی",
                ["کمتر از ۲ ساعت", "۲ تا ۴ ساعت", "۴ تا ۶ ساعت", "بیشتر از ۶ ساعت"],
            )
            university = st.selectbox("نوع دانشگاه", ["آزاد", "دولتی", "غیرانتفاعی", "مجازی"])
            major = st.text_input("رشته تحصیلی", placeholder="مثلاً مهندسی کامپیوتر")

        submitted = st.form_submit_button("ثبت اطلاعات و ادامه", type="primary", use_container_width=True)

    if not submitted:
        return

    if not major.strip():
        st.error("رشته تحصیلی را وارد کنید.")
        return

    def _parse_fa_int(value):
        normalized = str(value).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")).strip()
        return int(normalized) if normalized.isdigit() else None

    age = _parse_fa_int(age_raw)
    semester = _parse_fa_int(semester_raw)
    if age is None or not 15 <= age <= 80:
        st.error("سن را بین ۱۵ تا ۸۰ سال وارد کنید.")
        return
    if semester is None or not 1 <= semester <= 20:
        st.error("ترم تحصیلی را بین ۱ تا ۲۰ وارد کنید.")
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
    if st.session_state.get("day_ended"):
        st.success(f"روز {to_persian_digits(st.session_state['day_ended'])} با موفقیت ذخیره و پایان یافت.")
        st.session_state.day_ended = None
    st.subheader("ورود به مطالعه")

    # If a participant was already validated but has not yet completed
    # the seven demographic/educational fields, show the form directly.
    pending_code = st.session_state.get("pending_participant_code", "")
    pending_participant = st.session_state.get("pending_participant")

    if pending_code and pending_participant:
        current_participant = get_study_participant(pending_code) or pending_participant

        if not current_participant.get("consent", False):
            render_consent_page(pending_code, current_participant)
        else:
            existing_student = load_student(pending_code)

            if existing_student is not None:
                st.session_state.student_code = pending_code
                st.session_state.participant = current_participant
                st.session_state.student = existing_student
                st.session_state.pending_participant_code = ""
                st.session_state.pending_participant = None
                st.rerun()
            else:
                if st.session_state.get("consent_saved"):
                    st.success("رضایت با موفقیت ثبت شد.")
                    st.session_state.consent_saved = False
                st.info(f"کد پژوهشی {pending_code} تأیید شد. ابتدا اطلاعات شرکت‌کننده را تکمیل کنید.")
                render_participant_info_form(pending_code, current_participant)

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
                    st.session_state.pending_participant_code = code
                    st.session_state.pending_participant = participant
                    st.rerun()
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

real_study_day = get_study_day(student_code)

if real_study_day is None:
    st.error("تاریخ شروع مطالعه برای این شرکت‌کننده مشخص نیست.")
    st.stop()

study_day = real_study_day


study_date = get_study_date(student_code, study_day)
study_date_text = jalali_from_gregorian(study_date) if study_date else ""
st.markdown(
    f'<div class="study-meta">کد پژوهشی: {student_code} | روز {to_persian_digits(study_day)} از {to_persian_digits(7)} | تاریخ: {to_persian_digits(study_date_text)}</div>',
    unsafe_allow_html=True,
)


# ============================================================
# Completed
# ============================================================

if participant["status"] == "completed":
    if st.session_state.get("posttest_saved"):
        st.success("پس‌آزمون با موفقیت ثبت شد و مطالعه برای این کد پژوهشی تکمیل شد.")
        st.session_state.posttest_saved = False
    else:
        st.success("این مطالعه برای این کد پژوهشی تکمیل شده است.")
    st.info("از همکاری شما سپاسگزاریم.")
    st.stop()


# ============================================================
# Pretest — BOTH GROUPS
# ============================================================

if not has_assessment(student_code, "pretest"):
    st.warning(
        "مرحله اول مطالعه: پیش‌آزمون. "
        "این مرحله برای همه شرکت‌کنندگان یکسان است."
    )

    answers = questionnaire_form(
        "pretest_form",
        "پیش‌آزمون اهمال‌کاری",
    )

    if answers is not None:
        try:
            result, assessment_id = save_pretest(student, answers)

            if participant["group_type"] == "intervention":
                ensure_daily_interventions(student, 1, result)

            st.session_state["pretest_saved"] = True
            st.rerun()

        except Exception as exc:
            st.error(f"ثبت پیش‌آزمون انجام نشد: {exc}")

    st.stop()


# ============================================================
# Day 1–7 daily phase
# ============================================================

if 1 <= study_day <= 7:

    if participant["group_type"] == "control":
        st.subheader(f"برنامه امروز — روز {to_persian_digits(study_day)}")

        st.markdown(
            """
            <div class="card">
                <h3>روال معمول آموزشی</h3>
                <p>
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
        st.subheader(f"برنامه امروز — روز {to_persian_digits(study_day)}")

        pretest = get_assessment(student_code, "pretest")
        pretest_answers = get_assessment_responses(pretest[0]) if pretest else None
        base_result = calculate_intervention_result_cached(_student_cache_items(student), _answer_cache_items(pretest_answers)) if pretest_answers else None
        saved = ensure_daily_interventions(student, study_day, base_result) if base_result else []

        if not saved:
            st.error("برنامه امروز در پایگاه داده پیدا نشد.")
        else:
            st.markdown(
                f"""
                <div class="card">
                    <h3>برنامه امروز — روز {to_persian_digits(study_day)}</h3>
                    <p class="small">این برنامه متناسب با مرحله امروز تنظیم شده و تمرکز رفتاری آن ثابت می‌ماند.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            for index, row in enumerate(saved, start=1):
                intervention = row_to_intervention(row)
                render_intervention(intervention, index)

            st.divider()

            existing_log = get_daily_log(student_code, study_day)

            with st.form(f"daily_log_{study_day}"):
                primary_profile = saved[0][4] if saved else "general_procrastination"
                checkin_question = get_daily_checkin_question(primary_profile, study_day)
                st.markdown(f"**پایش کوتاه امروز**\n\n{checkin_question}")

                checkin_options = [
                    "خیلی کم",
                    "کم",
                    "متوسط",
                    "زیاد",
                    "خیلی زیاد",
                ]
                existing_checkin = (existing_log[9] if existing_log and len(existing_log) > 9 else "")
                checkin_answer = st.radio(
                    "پاسخ کوتاه امروز",
                    checkin_options,
                    index=checkin_options.index(existing_checkin) if existing_checkin in checkin_options else None,
                    horizontal=True,
                )

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
                minutes_raw = st.text_input(
                    "مدت اجرای فعالیت (دقیقه)",
                    value="",
                    placeholder="مثلاً ۳۰",
                    key=f"minutes_day_{student_code}_{study_day}",
                )
                normalized_minutes = str(minutes_raw).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")).strip()
                minutes = int(normalized_minutes) if normalized_minutes.isdigit() else None

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
                if checkin_answer is None:
                    st.error("پاسخ پایش کوتاه امروز را انتخاب کنید.")
                elif minutes is not None and (minutes < 0 or minutes > 600):
                    st.error("مدت اجرا باید بین صفر تا ۶۰۰ دقیقه باشد.")
                elif minutes is None and status != "not_started":
                    st.error("مدت اجرای فعالیت را وارد کنید.")
                else:
                    actual_minutes = minutes
                    if actual_minutes is None and existing_log:
                        actual_minutes = existing_log[4]
                    save_daily_log(
                        student_code=student_code,
                        day_number=study_day,
                        action_status=status,
                        actual_minutes=actual_minutes,
                        coach_used=bool(existing_log[5]) if existing_log else False,
                        notes=notes,
                        checkin_question=checkin_question,
                        checkin_answer=checkin_answer,
                    )
                    st.success("گزارش فعالیت امروز ثبت شد.")

    # --------------------------------------------------------
    # AI Coach — available to intervention group only
    # --------------------------------------------------------

    if participant["group_type"] == "intervention":
        st.divider()
        st.subheader("مربی هوشمند")

        saved = get_study_interventions(student_code, day_number=study_day)

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
                        # مربی باید آخرین پایش ذخیره‌شده امروز + نتیجه کامل پیش‌آزمون
                        # + پروفایل رفتاری + اطلاعات آموزشی/جمعیت‌شناختی را ببیند.
                        today_log = get_daily_log(student_code, study_day)
                        today_monitoring = build_today_monitoring(today_log)

                        # اگر فرم پایش امروز در همین صفحه مقدارهای تازه‌ای دارد،
                        # همان مقدارهای جاری را به مربی بده؛ حتی اگر هنوز دکمه
                        # «ثبت فعالیت امروز» زده نشده باشد. در غیر این صورت،
                        # آخرین داده ذخیره‌شده در پایگاه داده استفاده می‌شود.
                        if "status" in locals():
                            today_monitoring["status"] = status
                        if "minutes" in locals() and minutes is not None:
                            today_monitoring["minutes"] = minutes
                        if "notes" in locals():
                            today_monitoring["notes"] = notes or ""
                        if "checkin_question" in locals():
                            today_monitoring["checkin_question"] = checkin_question or ""
                        if "checkin_answer" in locals() and checkin_answer is not None:
                            today_monitoring["checkin_answer"] = checkin_answer

                        pretest = get_assessment(student_code, "pretest")
                        pretest_answers = (
                            get_assessment_responses(pretest[0])
                            if pretest
                            else None
                        )
                        questionnaire_result = None
                        if pretest_answers:
                            questionnaire_result = calculate_intervention_result_cached(
                                _student_cache_items(student),
                                _answer_cache_items(pretest_answers),
                            )

                        response = ai_coach(
                            level=primary["estimated_level"],
                            dominant_profile=primary["profile"],
                            intervention_name=primary["name"],
                            intervention_description=primary["description"],
                            student_message=student_message.strip(),
                            student_context=student,
                            questionnaire_result=questionnaire_result,
                            today_monitoring=today_monitoring,
                        )
                        response = str(response).replace("مداخله", "برنامه")
                        safe_response = html.escape(response).replace("\n", "<br>")

                        st.markdown(
                            f"""
                            <div class="card">
                                <h4>پیشنهاد مربی</h4>
                                <p>{safe_response}</p>
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
                                existing[4] if existing else None
                            ),
                            coach_used=True,
                            notes=(
                                existing[6] if existing else ""
                            ),
                            checkin_question=(
                                existing[8] if existing and len(existing) > 8 else ""
                            ),
                            checkin_answer=(
                                existing[9] if existing and len(existing) > 9 else ""
                            ),
                        )

                    except Exception as exc:
                        st.error(f"مربی هوشمند در دسترس نیست: {exc}")


# ============================================================
# End-of-day exit — intervention group
# ============================================================

if 1 <= study_day < 7 and participant["group_type"] == "intervention":
    st.divider()
    st.subheader("پایان روز")
    st.caption(
        "پس از ثبت فعالیت و در صورت نیاز استفاده از مربی هوشمند، "
        "برای خروج از مطالعه در این روز روی دکمه زیر بزن."
    )

    if st.button(
        "ذخیره اطلاعات و پایان روز",
        key=f"end_day_{study_day}",
        type="secondary",
        use_container_width=True,
    ):
        # Save the latest values again so changes are not lost when the user
        # exits without pressing the daily form's save button a second time.
        latest_log = get_daily_log(student_code, study_day)

        current_status = status if "status" in locals() else (
            latest_log[3] if latest_log else "not_started"
        )
        current_minutes = minutes if ("minutes" in locals() and minutes is not None) else (
            latest_log[4] if latest_log else None
        )
        current_notes = notes if "notes" in locals() else (
            latest_log[6] if latest_log else ""
        )
        current_checkin_question = (
            checkin_question if "checkin_question" in locals() else (
                latest_log[8] if latest_log and len(latest_log) > 8 else ""
            )
        )
        current_checkin_answer = (
            checkin_answer if "checkin_answer" in locals() else (
                latest_log[9] if latest_log and len(latest_log) > 9 else ""
            )
        )

        save_daily_log(
            student_code=student_code,
            day_number=study_day,
            action_status=current_status,
            actual_minutes=current_minutes,
            coach_used=bool(latest_log[5]) if latest_log else False,
            notes=current_notes,
            checkin_question=current_checkin_question,
            checkin_answer=current_checkin_answer,
        )

        st.session_state["day_ended"] = study_day
        st.session_state.student_code = ""
        st.session_state.student = None
        st.session_state.participant = None
        st.session_state.pending_participant_code = ""
        st.session_state.pending_participant = None
        st.rerun()


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
                f"{to_persian_digits(f'{posttest[2]:.1f}')} از {to_persian_digits(110)}",
            )

        if participant["status"] != "completed":
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

            complete_study_participant(student_code)

            st.success("پس‌آزمون با موفقیت ثبت شد.")

            c1, c2 = st.columns(2)
            post_total_text = to_persian_digits(f"{post_result['total_score']:.1f}")
            c1.metric(
                "نمره پس‌آزمون",
                f"{post_total_text} از {to_persian_digits(110)}",
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
            st.rerun()

        except Exception as exc:
            st.error(f"ثبت پس‌آزمون انجام نشد: {exc}")