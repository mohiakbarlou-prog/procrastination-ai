# intervention_engine.py
from typing import Dict, Any, List
from config import PROFILES, MAX_INTERVENTIONS


def _level_rank(level: str) -> int:
    return {
        "low": 0,
        "medium": 1,
        "high": 2,
    }.get(level, 0)


def normalize_procrastination_level(level) -> str:
    """تبدیل خروجی‌های رایج سطح اهمال‌کاری به low/medium/high."""
    if level is None:
        return "medium"

    if isinstance(level, str):
        text = level.strip().lower()
        mapping = {
            "low": "low",
            "medium": "medium",
            "high": "high",
            "پایین": "low",
            "متوسط": "medium",
            "بالا": "high",
            "1": "low",
            "2": "medium",
            "3": "high",
        }
        return mapping.get(text, "medium")

    try:
        value = int(level)
        return {1: "low", 2: "medium", 3: "high"}.get(value, "medium")
    except (TypeError, ValueError):
        return "medium"


def combine_intensity(profile_level: str, overall_level: str) -> str:
    """
    شدت نهایی مداخله:
    - پروفایل پایین: نگهدارنده
    - پروفایل متوسط: حداقل شدت متوسط، مگر اینکه سطح کلی بالا باشد
    - پروفایل بالا: شدت بالا
    """
    profile_rank = _level_rank(profile_level)
    overall_rank = _level_rank(overall_level)

    # سطح کلی فقط شدت را افزایش می‌دهد و نوع مداخله را عوض نمی‌کند.
    rank = max(profile_rank, overall_rank)

    return {0: "low", 1: "medium", 2: "high"}[rank]


def select_intervention(
    row: Dict[str, Any],
    profile_result: Dict[str, Any],
    overall_level: str,
) -> Dict[str, Any]:
    """
    انتخاب حداکثر دو مداخله بر اساس پروفایل رفتاری.
    ویژگی‌های فردی/آموزشی در این تابع نوع مداخله را تعیین نمی‌کنند.
    """
    overall_level = normalize_procrastination_level(overall_level)

    scores = profile_result.get("scores", {})
    levels = profile_result.get("levels", {})

    candidates = []
    for profile_key, score in scores.items():
        if score is None:
            continue

        profile_level = levels.get(profile_key, "unknown")
        if profile_level == "low":
            continue

        candidates.append(
            {
                "profile": profile_key,
                "score": score,
                "profile_level": profile_level,
                "intensity": combine_intensity(profile_level, overall_level),
            }
        )

    candidates.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    selected = candidates[:MAX_INTERVENTIONS]

    interventions = []
    for item in selected:
        profile = PROFILES[item["profile"]]
        intensity = item["intensity"]
        intervention = profile["interventions"][intensity]

        interventions.append(
            {
                "profile": item["profile"],
                "profile_name": profile["name"],
                "profile_score": item["score"],
                "profile_level": item["profile_level"],
                "intensity": intensity,
                "name": intervention["name"],
                "description": intervention["description"],
                "actions": intervention["actions"],
                "operational_note": profile.get("operational_note"),
            }
        )

    if not interventions:
        interventions = [
            {
                "profile": None,
                "profile_name": "پروفایل برجسته‌ای شناسایی نشد",
                "profile_score": None,
                "profile_level": "low",
                "intensity": "low",
                "name": "پیام نگهدارنده",
                "description": "در پروفایل‌های عملیاتی، الگوی برجسته‌ای برای مداخله اختصاصی مشاهده نشد.",
                "actions": [
                    "روند فعلی فعالیت‌های تحصیلی را حفظ کن."
                ],
                "operational_note": None,
            }
        ]

    return {
        "overall_level": overall_level,
        "interventions": interventions,
        "primary": interventions[0],
    }


# سازگاری با نسخه قبلی app.py
def choose_intervention(
    row: Dict[str, Any],
    overall_level: str = "medium",
    profile_result: Dict[str, Any] = None,
) -> Dict[str, Any]:
    if profile_result is None:
        from profile import create_profile
        profile_result = create_profile(row)

    result = select_intervention(
        row=row,
        profile_result=profile_result,
        overall_level=overall_level,
    )

    # کلیدهای سازگار با کدهای قبلی
    result["profile"] = result["primary"]["profile"]
    result["intervention"] = result["primary"]
    result["scores"] = profile_result.get("scores", {})
    return result


def personalize_presentation(
    intervention: Dict[str, Any],
    student_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    فقط نحوه ارائه را شخصی‌سازی می‌کند.
    از سن/جنسیت/دانشگاه/رشته برای تعیین نوع مداخله استفاده نمی‌شود.
    """
    degree = str(student_data.get("degree", "")).strip()
    semester = student_data.get("semester")
    daily_use = str(student_data.get("daily_use", "")).strip()

    presentation = {
        "style": "کوتاه و اجرایی",
        "time_note": None,
        "detail_note": None,
    }

    if degree == "کارشناسی":
        presentation["detail_note"] = "دستورالعمل‌ها به صورت مرحله‌ای و کوتاه ارائه شوند."
    elif degree in {"ارشد", "دکتری"}:
        presentation["detail_note"] = "دستورالعمل‌ها با تأکید بیشتر بر خودراه‌بری و برنامه‌ریزی مستقل ارائه شوند."

    try:
        sem = int(semester)
        if sem <= 3:
            presentation["style"] = "مرحله‌ای و بسیار مشخص"
        elif sem <= 6:
            presentation["style"] = "کوتاه و اجرایی"
        else:
            presentation["style"] = "فشرده و خودراهبر"
    except (TypeError, ValueError):
        pass

    if "4–6" in daily_use or "4-6" in daily_use:
        presentation["time_note"] = "پیشنهادها در بازه‌های کوتاه و مشخص ارائه شوند."
    elif ">6" in daily_use:
        presentation["time_note"] = "از برنامه‌های طولانی پرهیز و فعالیت به بازه‌های کوتاه تقسیم شود."

    return {
        **intervention,
        "presentation": presentation,
    }
