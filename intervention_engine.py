from typing import Dict, Any
from config import PROFILES, MAX_INTERVENTIONS


def _level_rank(level: str) -> int:
    return {"low": 0, "medium": 1, "high": 2}.get(level, 0)


def normalize_procrastination_level(level):
    if level is None:
        return None
    if isinstance(level, str):
        text = level.strip().lower()
        mapping = {
            "low": "low", "medium": "medium", "high": "high",
            "پایین": "low", "متوسط": "medium", "بالا": "high",
        }
        if text in mapping:
            return mapping[text]
        if text == "1":
            return "low"
        if text == "2":
            return "medium"
        if text == "3":
            return "high"
        if text == "0":
            return "low"
        return None
    try:
        value = int(level)
        if value in (0, 1, 2):
            return {0: "low", 1: "medium", 2: "high"}[value]
        if value in (1, 2, 3):
            return {1: "low", 2: "medium", 3: "high"}[value]
    except (TypeError, ValueError):
        pass
    return None


def combine_intensity(profile_level: str, overall_level: str) -> str:
    profile_level = normalize_procrastination_level(profile_level) or "low"
    overall_level = normalize_procrastination_level(overall_level) or "low"
    rank = max(_level_rank(profile_level), _level_rank(overall_level))
    return {0: "low", 1: "medium", 2: "high"}[rank]


def select_intervention(row: Dict[str, Any], profile_result: Dict[str, Any], overall_level: str) -> Dict[str, Any]:
    overall_level = normalize_procrastination_level(overall_level)
    if overall_level is None:
        raise ValueError("سطح کلی دریافت‌شده برای انتخاب برنامه معتبر نیست.")
    scores = profile_result.get("scores", {})
    levels = profile_result.get("levels", {})
    candidates = []
    for profile_key, score in scores.items():
        if score is None:
            continue
        profile_level = normalize_procrastination_level(levels.get(profile_key))
        if profile_level is None or profile_level == "low":
            continue
        candidates.append({
            "profile": profile_key,
            "score": float(score),
            "profile_level": profile_level,
            "intensity": combine_intensity(profile_level, overall_level),
        })
    candidates.sort(key=lambda x: x["score"], reverse=True)
    interventions = []
    for item in candidates[:MAX_INTERVENTIONS]:
        profile = PROFILES[item["profile"]]
        intensity = item["intensity"]
        intervention = profile["interventions"][intensity]
        interventions.append({
            "profile": item["profile"],
            "profile_name": profile["name"],
            "profile_score": item["score"],
            "profile_level": item["profile_level"],
            "intensity": intensity,
            "name": intervention["name"],
            "description": intervention["description"],
            "actions": list(intervention.get("actions", [])),
            "operational_note": profile.get("operational_note"),
        })
    if not interventions:
        interventions = [{
            "profile": None,
            "profile_name": "پروفایل برجسته‌ای شناسایی نشد",
            "profile_score": None,
            "profile_level": "low",
            "intensity": "low",
            "name": "پیام نگهدارنده",
            "description": "در پروفایل‌های عملیاتی، الگوی برجسته‌ای برای برنامه اختصاصی مشاهده نشد.",
            "actions": ["روند فعلی فعالیت‌های تحصیلی را حفظ کن."],
            "operational_note": None,
        }]
    return {"overall_level": overall_level, "interventions": interventions, "primary": interventions[0]}


def choose_intervention(row: Dict[str, Any], overall_level: str = "medium", profile_result: Dict[str, Any] = None) -> Dict[str, Any]:
    if profile_result is None:
        from profile import create_profile
        profile_result = create_profile(row)
    result = select_intervention(row=row, profile_result=profile_result, overall_level=overall_level)
    result["profile"] = result["primary"]["profile"]
    result["intervention"] = result["primary"]
    result["scores"] = profile_result.get("scores", {})
    return result


def personalize_presentation(intervention: Dict[str, Any], student_data: Dict[str, Any]) -> Dict[str, Any]:
    degree = str(student_data.get("degree", "")).strip()
    semester = student_data.get("semester")
    daily_use = str(student_data.get("daily_use", "")).strip()
    presentation = {"style": "کوتاه و اجرایی", "time_note": None, "detail_note": None}
    if degree == "کارشناسی":
        presentation["detail_note"] = "دستورالعمل‌ها به صورت مرحله‌ای و کوتاه ارائه شوند."
    elif degree in {"کارشناسی ارشد", "ارشد"}:
        presentation["detail_note"] = "دستورالعمل‌ها با تأکید بیشتر بر خودراه‌بری و برنامه‌ریزی مستقل ارائه شوند."
    elif degree == "دکتری":
        presentation["detail_note"] = "توضیحات فشرده و خودراهبر با تأکید بر مدیریت مستقل فعالیت ارائه شوند."
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
    elif "بیشتر از ۶" in daily_use or ">6" in daily_use:
        presentation["time_note"] = "از برنامه‌های طولانی پرهیز و فعالیت به بازه‌های کوتاه تقسیم شود."
    return {**intervention, "presentation": presentation}
