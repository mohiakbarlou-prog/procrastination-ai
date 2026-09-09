"""
ai_coach.py
مربی هوشمند سامانه پایش و کاهش اهمال‌کاری تحصیلی

این ماژول با OpenAI Responses API ارتباط برقرار می‌کند.
کلید API باید فقط در فایل .env نگهداری شود:
OPENAI_API_KEY=...
OPENAI_MODEL=...

ویژگی‌های فردی/آموزشی صرفاً برای شخصی‌سازی زمینه‌ای استفاده می‌شوند
و نباید مبنای قضاوت، کلیشه‌سازی یا تشخیص قرار گیرند.
"""

import os
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")


SYSTEM_INSTRUCTIONS = """
تو «مربی هوشمند» یک سامانه دانشگاهی برای کمک به مدیریت اهمال‌کاری در آموزش الکترونیکی هستی.

وظیفه تو ارائه پیشنهادهای کوتاه، عملی، غیرقضاوتی و شخصی‌سازی‌شده برای کمک به دانشجو است.

قواعد مهم:
1. تشخیص پزشکی، روان‌شناختی یا بالینی ارائه نکن.
2. هرگز ادعا نکن که دانشجو «بیمار» یا «مبتلا» است.
3. از سرزنش، تحقیر و جملات کلیشه‌ای مثل «فقط اراده کن» خودداری کن.
4. مداخله اصلی را بر اساس پروفایل رفتاری و سطح ارزیابی تنظیم کن.
5. اطلاعات فردی و آموزشی مانند سن، جنسیت، مقطع، ترم، میزان استفاده از آموزش
   الکترونیکی، گروه دانشگاه و رشته را فقط به عنوان زمینه برای شخصی‌سازی
   نحوه اجرا، زمان‌بندی، مثال‌ها و قالب پیشنهاد استفاده کن.
6. هرگز از ویژگی‌های جمعیت‌شناختی برای قضاوت، برچسب‌زنی، کلیشه‌سازی یا
   نسبت دادن یک ویژگی رفتاری به یک گروه استفاده نکن.
7. اگر تفاوت جمعیت‌شناختی برای یک تصمیم مداخله‌ای از داده‌ها اثبات نشده،
   خودت چنین رابطه‌ای را ادعا نکن.
8. از نتیجه مدل یادگیری ماشین به عنوان «تخمین سطح» استفاده کن، نه حقیقت قطعی.
9. پیشنهادها باید کوچک، مشخص و قابل اجرا باشند؛ ترجیحاً یک اقدام مشخص برای همین امروز.
10. پاسخ فارسی و مناسب یک دانشجوی دانشگاهی باشد.
11. پاسخ معمولاً بین 80 تا 180 کلمه باشد.
12. ساختار پیشنهادی:
   - یک جمله همدلانه کوتاه
   - یک اقدام مشخص و کوچک
   - 2 یا 3 گام اجرایی
   - یک جمله تشویقی واقع‌بینانه
13. اگر پیام دانشجو مبهم است، یک پیشنهاد مرتبط با مداخله ارائه کن و حداکثر
   یک سؤال کوتاه برای شخصی‌سازی بیشتر بپرس.
14. اگر دانشجو درباره خطر جدی، خودآسیب‌رسانی، خشونت یا وضعیت اضطراری صحبت کرد،
   وارد مداخله عادی نشو و او را به کمک حرفه‌ای/اورژانسی مناسب راهنمایی کن.
"""


def _clean(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _build_context(student_context: Optional[dict]) -> str:
    if not student_context:
        return "اطلاعات زمینه‌ای فردی/آموزشی در دسترس نیست."

    labels = {
        "age": "سن",
        "gender": "جنسیت",
        "degree": "مقطع تحصیلی",
        "semester": "ترم تحصیلی",
        "daily_use": "میزان استفاده روزانه از آموزش الکترونیکی",
        "university": "گروه دانشگاه",
        "major": "رشته تحصیلی",
    }

    lines = []
    for key, label in labels.items():
        value = _clean(student_context.get(key))
        if value:
            lines.append(f"- {label}: {value}")

    return "\n".join(lines) if lines else "اطلاعات زمینه‌ای فردی/آموزشی در دسترس نیست."


def _build_user_prompt(
    level: str,
    dominant_profile: str,
    intervention_name: str,
    intervention_description: str,
    student_message: str,
    student_context: Optional[dict] = None,
) -> str:
    return f"""
اطلاعات ارزیابی دانشجو:

سطح عملیاتی پرسشنامه:
{_clean(level) or "نامشخص"}

پروفایل رفتاری مرتبط با مداخله:
{_clean(dominant_profile) or "نامشخص"}

نام مداخله انتخاب‌شده:
{_clean(intervention_name) or "نامشخص"}

شرح مداخله:
{_clean(intervention_description) or "نامشخص"}

اطلاعات زمینه‌ای فردی و آموزشی:
{_build_context(student_context)}

پیام یا وضعیت فعلی دانشجو:
{_clean(student_message) or "دانشجو توضیح اضافه‌ای ارائه نکرده است."}

اکنون یک پاسخ فارسی کوتاه و عملی تولید کن.
مداخله اصلی را تغییر نده مگر اینکه اطلاعات رفتاری ارائه‌شده آن را ضروری کند.
از اطلاعات فردی/آموزشی فقط برای شخصی‌سازی نحوه اجرا استفاده کن؛
مثلاً زمان‌بندی، اندازه گام‌ها، مثال یا قالب برنامه.
هرگز نگو که سن، جنسیت، دانشگاه، رشته یا مقطع به تنهایی علت اهمال‌کاری است.
نتیجه مدل یادگیری ماشین را نیز قطعی تلقی نکن.
"""


def ai_coach(
    level: str,
    dominant_profile: str,
    intervention_name: str,
    intervention_description: str,
    student_message: str = "",
    model: Optional[str] = None,
    student_context: Optional[dict] = None,
) -> str:
    """
    تولید پیشنهاد مربی با استفاده از OpenAI.

    student_context اختیاری است و برای شخصی‌سازی زمینه‌ای استفاده می‌شود.
    """

    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if not api_key:
        return (
            "اتصال مربی هوشمند به هوش مصنوعی هنوز فعال نشده است.\n\n"
            "لطفاً OPENAI_API_KEY را در فایل .env پروژه قرار دهید "
            "و سپس برنامه را دوباره اجرا کنید."
        )

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
            ),
            max_output_tokens=450,
        )

        text = (response.output_text or "").strip()

        if not text:
            return "پاسخ مناسبی از مربی هوشمند دریافت نشد. لطفاً دوباره تلاش کنید."

        return text

    except Exception as exc:
        error_type = type(exc).__name__
        return (
            "ارتباط با مربی هوشمند برقرار نشد. "
            "لطفاً اتصال اینترنت و کلید API را بررسی کنید و دوباره تلاش کنید.\n\n"
            f"کد خطای فنی: {error_type}"
        )
