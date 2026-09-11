import html
import os
from typing import Optional

from openai import OpenAI
import streamlit as st

# ============================================================
# Provider configuration — Groq (OpenAI-compatible)
# ============================================================
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

FALLBACK_MODEL = "llama-3.3-70b-versatile"


def _resolve_default_model() -> str:
    value = (os.getenv("GROQ_MODEL") or "").strip()
    if value:
        return value
    try:
        value = str(st.secrets.get("GROQ_MODEL", "")).strip()
    except Exception:
        value = ""
    return value or FALLBACK_MODEL


DEFAULT_MODEL = _resolve_default_model()

SYSTEM_INSTRUCTIONS = """
تو مربی هوشمند سامانه «مدیریت اهمال‌کاری تحصیلی در آموزش الکترونیکی» هستی.

وظیفه تو ارائه پاسخ کوتاه، عملی، غیرقضاوتی و شخصی‌سازی‌شده به دانشجوست.

اطلاعاتی که ممکن است در اختیار تو باشد:
1) اطلاعات جمعیت‌شناختی و آموزشی دانشجو: سن، جنسیت، مقطع، ترم، میزان استفاده روزانه، نوع دانشگاه و رشته.
2) نتیجه کامل پرسشنامه ۲۲ سؤالی.
3) برآورد مدل یادگیری ماشین.
4) برنامه‌ی امروز.
5) آخرین پایش امروز.
6) پیام فعلی دانشجو.

قواعد:
- پاسخ را بر اساس مجموع اطلاعات موجود بساز.
- الگوی رفتاری و شواهد پرسشنامه و پایش، مبنای اصلی توصیه باشند.
- از کلیشه یا قضاوت درباره جنسیت، رشته، دانشگاه، سن یا مقطع استفاده نکن.
- estimated level فقط «برآورد مدل» است، نه تشخیص قطعی.
- هرگز به دانشجو برچسب روان‌شناختی/تشخیصی نزن.
- درباره رفتار مشخص صحبت کن: شروع کار، مطالعه، زمان‌بندی، حواس‌پرتی، کمک‌خواهی، فعالیت گروهی.
- برنامه امروز را عوض نکن؛ اجرا را شخصی‌سازی کن.
- اگر فعالیت شروع نشده، یک گام بسیار کوچک پیشنهاد کن.
- اگر ناقص بوده، روی تکمیل گام بعدی تمرکز کن.
- اگر کامل بوده، پاسخ را بر تثبیت رفتار متمرکز کن.
- اگر دانشجو مانعی گفته، مستقیماً به همان مانع پاسخ بده.
- پاسخ ۳ تا ۶ جمله باشد و حداکثر ۳ گام عملی کوتاه داشته باشد.
- از توصیه‌های کلی پرهیز کن.
- اگر اطلاعاتی نیست، حدس نزن.

پاسخ خود را مستقیماً و به زبان فارسی بنویس. از مقدمه‌چینی پرهیز کن.
""".strip()


def _clean(value):
    if value is None:
        return ""
    return str(value).strip()


def _build_context(student_context):
    if not student_context:
        return "اطلاعات جمعیت‌شناختی/آموزشی در دسترس نیست."
    labels = {
        "age": "سن", "gender": "جنسیت", "degree": "مقطع",
        "semester": "ترم", "daily_use": "استفاده روزانه",
        "university": "نوع دانشگاه", "major": "رشته",
    }
    parts = []
    for key, label in labels.items():
        value = _clean(student_context.get(key))
        if value:
            parts.append(f"{label}: {value}")
    return " | ".join(parts) if parts else "اطلاعات در دسترس نیست."


def _level_fa(level):
    return {
        "low": "پایین", "medium": "متوسط", "high": "بالا",
        "پایین": "پایین", "متوسط": "متوسط", "بالا": "بالا",
    }.get(_clean(level).lower(), _clean(level))


def _profile_summary(questionnaire_result):
    if not questionnaire_result:
        return "نتیجه پرسشنامه در دسترس نیست."
    lines = [
        f"نمره کل پرسشنامه: {_clean(questionnaire_result.get('total_score'))} از ۱۱۰",
        f"سطح پرسشنامه: {_level_fa(questionnaire_result.get('overall_level', ''))}",
        f"سطح برآوردشده مدل: {_level_fa(questionnaire_result.get('estimated_level', ''))}",
    ]
    profile_result = questionnaire_result.get("profile_result") or {}
    if isinstance(profile_result, dict):
        try:
            ranked = sorted(
                profile_result.items(),
                key=lambda item: float(item[1].get("score", item[1]) if isinstance(item[1], dict) else item[1]),
                reverse=True,
            )
        except Exception:
            ranked = list(profile_result.items())
        profile_names = {
            "task_initiation": "تأخیر در شروع کار",
            "educational_content": "تأخیر در مطالعه محتوا",
            "deadline_time": "مدیریت مهلت و زمان",
            "participation": "حضور و مشارکت آنلاین",
            "task_difficulty": "دشواری تکلیف",
            "digital_distraction": "حواس‌پرتی دیجیتال",
            "help_seeking": "تأخیر در کمک‌خواهی",
            "group_activity": "تأخیر در فعالیت گروهی",
            "stress_guilt": "استرس و احساس گناه",
            "general_procrastination": "اهمال‌کاری عمومی",
        }
        shown = []
        for key, value in ranked[:3]:
            if isinstance(value, dict):
                score = value.get("score", "")
                level = value.get("level", "")
            else:
                score = value
                level = ""
            name = profile_names.get(key, key)
            shown.append(f"- {name}: امتیاز {score}، سطح {_level_fa(level)}")
        if shown:
            lines.append("الگوهای رفتاری برجسته:\n" + "\n".join(shown))
    return "\n".join(lines)


def _monitoring_summary(today_monitoring):
    if not today_monitoring:
        return "پایش امروز ثبت نشده است."
    status_labels = {
        "not_started": "هنوز شروع نکردم",
        "partial": "بخشی از فعالیت را انجام دادم",
        "completed": "کامل انجام دادم",
    }
    status = status_labels.get(_clean(today_monitoring.get("status")), _clean(today_monitoring.get("status")))
    lines = [f"وضعیت اجرای فعالیت امروز: {status}"]
    minutes = today_monitoring.get("minutes")
    if minutes not in (None, ""):
        lines.append(f"مدت اجرا: {minutes} دقیقه")
    question = _clean(today_monitoring.get("checkin_question"))
    answer = _clean(today_monitoring.get("checkin_answer"))
    notes = _clean(today_monitoring.get("notes"))
    if question:
        lines.append(f"سؤال پایش: {question}")
    if answer:
        lines.append(f"پاسخ پایش: {answer}")
    if notes:
        lines.append(f"یادداشت: {notes}")
    return "\n".join(lines)


def _build_user_prompt(level, dominant_profile, intervention_name,
                       intervention_description, student_message,
                       student_context, questionnaire_result, today_monitoring):
    return f"""
اطلاعات دانشجو:
{_build_context(student_context)}

نتیجه پرسشنامه:
{_profile_summary(questionnaire_result)}

برنامه امروز:
نام برنامه: {_clean(intervention_name)}
توضیح: {_clean(intervention_description)}
الگوی اصلی: {_clean(dominant_profile)}
سطح برآوردی مدل: {_level_fa(level)}

پایش امروز:
{_monitoring_summary(today_monitoring)}

پیام دانشجو:
{_clean(student_message)}

اکنون پاسخ مربی را بنویس — مستقیماً به پیام دانشجو و با توجه به پایش امروز و برنامه، قابل اجرا و شخصی‌سازی‌شده.

پاسخ به فارسی، مستقیم و بدون مقدمه‌چینی.
""".strip()

def _debug_error(exc):
    """نمایش خطای واقعی برای دیباگ — موقت"""
    return f"[DEBUG] {type(exc).__name__}: {str(exc)[:500]}"

def _friendly_error(exc):
    text = f"{type(exc).__name__}: {exc}"
    lowered = text.lower()
    if "ratelimit" in lowered or "rate_limit" in lowered or "429" in lowered:
        return "مربی هوشمند الان به دلیل محدودیت مصرف سرویس، موقتاً در دسترس نیست. لطفاً چند دقیقه دیگر امتحان کنید."
    if "authentication" in lowered or "invalid_api_key" in lowered or "401" in lowered:
        return "کلید دسترسی مربی هوشمند معتبر نیست. لطفاً به پژوهشگر اطلاع دهید."
    if "quota" in lowered or "402" in lowered or "credit" in lowered:
        return "سهمیه‌ی سرویس مربی هوشمند به پایان رسیده است. لطفاً به پژوهشگر اطلاع دهید."
    if "connection" in lowered or "timeout" in lowered or "network" in lowered:
        return "ارتباط با مربی هوشمند برقرار نشد. لطفاً اتصال اینترنت را بررسی کنید."
    if "model" in lowered and ("not found" in lowered or "does not exist" in lowered or "invalid" in lowered):
        return "مدل مربی هوشمند در دسترس نیست. لطفاً به پژوهشگر اطلاع دهید."
    short = text[:200]
    return f"مربی هوشمند در حال حاضر در دسترس نیست. لطفاً بعداً امتحان کنید. (کد: {short})"


def _extract_text(response):
    if not response or not getattr(response, "choices", None):
        return ""
    choice = response.choices[0]
    message = getattr(choice, "message", None)
    if message is None:
        return ""
    content = getattr(message, "content", None)
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
            elif isinstance(item, str):
                parts.append(item)
        joined = " ".join(p for p in parts if p).strip()
        if joined:
            return joined
    return ""


def ai_coach(
    level: str,
    dominant_profile: str,
    intervention_name: str,
    intervention_description: str,
    student_message: str = "",
    model: Optional[str] = None,
    student_context: Optional[dict] = None,
    questionnaire_result: Optional[dict] = None,
    today_monitoring: Optional[dict] = None,
) -> str:
    api_key = _clean(os.getenv("GROQ_API_KEY"))
    if not api_key:
        try:
            api_key = _clean(st.secrets.get("GROQ_API_KEY", ""))
        except Exception:
            api_key = ""
    if not api_key:
        return "کلید دسترسی مربی هوشمند تنظیم نشده است."

    try:
        client = OpenAI(api_key=api_key, base_url=GROQ_BASE_URL)
        response = client.chat.completions.create(
            model=model or DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                {"role": "user", "content": _build_user_prompt(
                    level=level, dominant_profile=dominant_profile,
                    intervention_name=intervention_name,
                    intervention_description=intervention_description,
                    student_message=student_message,
                    student_context=student_context,
                    questionnaire_result=questionnaire_result,
                    today_monitoring=today_monitoring,
                )},
            ],
            max_tokens=800,
            temperature=0.7,
        )
        text = _clean(_extract_text(response))
        if text:
            return html.unescape(text)
        return "مربی هوشمند این بار پاسخی برنگرداند. لطفاً دوباره تلاش کنید."
      except Exception as exc:
        return _debug_error(exc)