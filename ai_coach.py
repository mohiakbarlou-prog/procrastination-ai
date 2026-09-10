import html
import os
from typing import Optional

from openai import OpenAI
import streamlit as st

# ============================================================
# Model configuration
# ============================================================
# مدل پیش‌فرض gpt-4o-mini است: ارزان، سریع، با سهمیه‌ی generous
# می‌توانی از طریق متغیر محیطی OPENAI_MODEL مدل را عوض کنی.
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

SYSTEM_INSTRUCTIONS = """
تو مربی هوشمند سامانه «مدیریت اهمال‌کاری تحصیلی در آموزش الکترونیکی» هستی.

وظیفه تو ارائه پاسخ کوتاه، عملی، غیرقضاوتی و شخصی‌سازی‌شده به دانشجوست.

اطلاعاتی که ممکن است در اختیار تو باشد:
1) اطلاعات جمعیت‌شناختی و آموزشی دانشجو: سن، جنسیت، مقطع، ترم، میزان استفاده روزانه از آموزش الکترونیکی، نوع دانشگاه و رشته.
2) نتیجه کامل پرسشنامه ۲۲ سؤالی، شامل نمره کل، سطح پرسشنامه و الگوهای رفتاری.
3) برآورد مدل یادگیری ماشین (estimated level).
4) برنامه‌ای که برای امروز انتخاب شده است.
5) آخرین پایش ثبت‌شده امروز: وضعیت اجرای فعالیت، مدت اجرا، پاسخ پایش کوتاه و یادداشت دانشجو.
6) پیام فعلی دانشجو.

قواعد:
- پاسخ را بر اساس مجموع اطلاعات موجود بساز، نه فقط بر اساس یک متغیر.
- الگوی رفتاری و شواهد رفتاری پرسشنامه و پایش روزانه، مبنای اصلی توصیه باشند.
- اطلاعات جمعیت‌شناختی و آموزشی را برای شخصی‌سازی مثال، زمان‌بندی، حجم کار، سطح توضیح و شیوه ارائه به کار ببر؛ از کلیشه یا قضاوت درباره جنسیت، رشته، دانشگاه، سن یا مقطع استفاده نکن.
- estimated level فقط «برآورد مدل» است و نباید به عنوان تشخیص قطعی یا واقعیت قطعی بیان شود.
- هرگز به دانشجو نگو «تو اهمال‌کار هستی»، «سطحت بالاست» یا او را با برچسب روان‌شناختی/تشخیصی توصیف نکن.
- درباره رفتار مشخص صحبت کن: شروع کار، مطالعه محتوا، زمان‌بندی، حواس‌پرتی، کمک‌خواهی، فعالیت گروهی و مانند آن.
- برنامه امروز را عوض نکن؛ در چارچوب همان برنامه، اجرای آن را با توجه به شرایط دانشجو شخصی‌سازی کن.
- اگر پایش امروز نشان می‌دهد فعالیت هنوز شروع نشده، یک گام بسیار کوچک و قابل اجرا پیشنهاد کن.
- اگر فعالیت ناقص بوده، روی تکمیل گام بعدی تمرکز کن و کل کار را دوباره تعریف نکن.
- اگر فعالیت کامل بوده، پاسخ را بر تثبیت رفتار و گام بعدی متمرکز کن.
- اگر دانشجو مشکل یا مانعی را در پیام خود گفته، مستقیماً به همان مانع پاسخ بده.
- پاسخ معمولاً ۳ تا ۶ جمله باشد و در صورت نیاز حداکثر ۳ گام عملی کوتاه داشته باشد.
- از توصیه‌های کلی و تکراری مثل «برنامه‌ریزی کن و موفق باشی» پرهیز کن.
- اگر اطلاعاتی وجود ندارد، آن را حدس نزن.
""".strip()


def _clean(value):
    if value is None:
        return ""
    return str(value).strip()


def _build_context(student_context: Optional[dict]) -> str:
    if not student_context:
        return "اطلاعات جمعیت‌شناختی/آموزشی در دسترس نیست."

    labels = {
        "age": "سن",
        "gender": "جنسیت",
        "degree": "مقطع",
        "semester": "ترم",
        "daily_use": "استفاده روزانه از آموزش الکترونیکی",
        "university": "نوع دانشگاه",
        "major": "رشته",
    }
    parts = []
    for key, label in labels.items():
        value = _clean(student_context.get(key))
        if value:
            parts.append(f"{label}: {value}")
    return " | ".join(parts) if parts else "اطلاعات جمعیت‌شناختی/آموزشی در دسترس نیست."


def _level_fa(level: str) -> str:
    return {
        "low": "پایین",
        "medium": "متوسط",
        "high": "بالا",
        "پایین": "پایین",
        "متوسط": "متوسط",
        "بالا": "بالا",
    }.get(_clean(level).lower(), _clean(level))


def _profile_summary(questionnaire_result: Optional[dict]) -> str:
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
            "educational_content": "تأخیر در مطالعه محتوای آموزشی",
            "deadline_time": "مدیریت مهلت و زمان",
            "participation": "حضور و مشارکت آنلاین",
            "task_difficulty": "مواجهه با دشواری تکلیف",
            "digital_distraction": "حواس‌پرتی دیجیتال",
            "help_seeking": "تأخیر در کمک‌خواهی",
            "group_activity": "تأخیر در فعالیت گروهی",
            "stress_guilt": "استرس و احساس گناه",
            "general_procrastination": "اهمال‌کاری عمومی",
        }
        shown = []
        # فقط ۳ الگوی برتر را می‌فرستیم تا مصرف توکن کم شود.
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

    # پاسخ‌های خام ۲۲ سؤال ارسال نمی‌شوند تا مصرف توکن کاهش یابد.
    # الگوهای برتر و نمره‌ی کل، اطلاعات کافی برای مربی فراهم می‌کنند.

    return "\n".join(lines)


def _monitoring_summary(today_monitoring: Optional[dict]) -> str:
    if not today_monitoring:
        return "پایش امروز ثبت نشده است."

    status_labels = {
        "not_started": "هنوز شروع نکردم",
        "partial": "بخشی از فعالیت را انجام دادم",
        "completed": "کامل انجام دادم",
    }
    status = status_labels.get(
        _clean(today_monitoring.get("status")),
        _clean(today_monitoring.get("status")),
    )
    minutes = today_monitoring.get("minutes")
    notes = _clean(today_monitoring.get("notes"))
    question = _clean(today_monitoring.get("checkin_question"))
    answer = _clean(today_monitoring.get("checkin_answer"))

    lines = [f"وضعیت اجرای فعالیت امروز: {status}"]
    if minutes not in (None, ""):
        lines.append(f"مدت اجرای ثبت‌شده: {minutes} دقیقه")
    if question:
        lines.append(f"سؤال پایش: {question}")
    if answer:
        lines.append(f"پاسخ پایش: {answer}")
    if notes:
        lines.append(f"یادداشت امروز: {notes}")
    return "\n".join(lines)


def _build_user_prompt(
    level: str,
    dominant_profile: str,
    intervention_name: str,
    intervention_description: str,
    student_message: str,
    student_context: Optional[dict],
    questionnaire_result: Optional[dict],
    today_monitoring: Optional[dict],
) -> str:
    return f"""
اطلاعات زمینه‌ای دانشجو:
{_build_context(student_context)}

نتیجه پرسشنامه:
{_profile_summary(questionnaire_result)}

برنامه امروز:
نام داخلی برنامه: {_clean(intervention_name)}
توضیح برنامه: {_clean(intervention_description)}
الگوی رفتاری اصلی: {_clean(dominant_profile)}
سطح برآوردشده مدل: {_level_fa(level)}

پایش امروز:
{_monitoring_summary(today_monitoring)}

پیام فعلی دانشجو:
{_clean(student_message)}

اکنون یک پاسخ مربی بده که مستقیماً به پیام دانشجو پاسخ دهد و برنامه امروز را با توجه به اطلاعات بالا، به‌ویژه پایش امروز و نتیجه پرسشنامه، قابل اجرا و شخصی‌سازی کند.
""".strip()


def _friendly_error(exc: Exception) -> str:
    """تبدیل خطاهای OpenAI به پیام فارسی قابل‌فهم برای کاربر."""
    text = f"{type(exc).__name__}: {exc}"
    lowered = text.lower()

    # Rate limit (سهمیه تمام شده)
    if "ratelimit" in lowered or "rate_limit" in lowered or "429" in lowered:
        return (
            "مربی هوشمند در حال حاضر به دلیل محدودیت مصرف سرویس، موقتاً در دسترس نیست. "
            "لطفاً چند ساعت دیگر دوباره امتحان کنید. اگر این پیام تکرار شد، "
            "این موضوع را به پژوهشگر اطلاع دهید."
        )

    # خطای احراز هویت / کلید نامعتبر
    if "authentication" in lowered or "invalid_api_key" in lowered or "401" in lowered:
        return (
            "کلید دسترسی مربی هوشمند معتبر نیست. "
            "لطفاً تنظیمات سامانه را بررسی کنید."
        )

    # خطای سهمیه‌ی حساب
    if "insufficient_quota" in lowered or "quota" in lowered or "402" in lowered:
        return (
            "سهمیه‌ی سرویس مربی هوشمند به پایان رسیده است. "
            "این موضوع را به پژوهشگر اطلاع دهید."
        )

    # خطای شبکه / اتصال
    if "connection" in lowered or "timeout" in lowered or "network" in lowered:
        return (
            "ارتباط با مربی هوشمند برقرار نشد. "
            "لطفاً اتصال اینترنت خود را بررسی کنید و دوباره تلاش کنید."
        )

    # خطای مدل نامعتبر
    if "model" in lowered and ("not found" in lowered or "does not exist" in lowered or "invalid" in lowered):
        return (
            "مدل مربی هوشمند در دسترس نیست. "
            "این موضوع را به پژوهشگر اطلاع دهید."
        )

    # سایر خطاها — پیام عمومی با جزئیات فنی کوتاه
    short = text[:200]
    return (
        "مربی هوشمند در حال حاضر در دسترس نیست. "
        f"لطفاً بعداً دوباره امتحان کنید. (کد خطا: {short})"
    )


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
    # ابتدا Environment Variable و سپس Streamlit Secrets بررسی می‌شود.
    api_key = _clean(os.getenv("OPENAI_API_KEY"))

    if not api_key:
        try:
            api_key = _clean(st.secrets.get("OPENAI_API_KEY", ""))
        except Exception:
            api_key = ""

    if not api_key:
        return "کلید دسترسی مربی هوشمند تنظیم نشده است. لطفاً تنظیمات سامانه را بررسی کنید."

    try:
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=model or DEFAULT_MODEL,
            instructions=SYSTEM_INSTRUCTIONS,
            input=_build_user_prompt(
                level=level,
                dominant_profile=dominant_profile,
                intervention_name=intervention_name,
                intervention_description=intervention_description,
                student_message=student_message,
                student_context=student_context,
                questionnaire_result=questionnaire_result,
                today_monitoring=today_monitoring,
            ),
            max_output_tokens=350,
        )
        text = getattr(response, "output_text", None)
        if text:
            return html.unescape(_clean(text))
        return "در حال حاضر پاسخی از مربی هوشمند دریافت نشد."
    except Exception as exc:
        return _friendly_error(exc)