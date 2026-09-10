from typing import Dict, Any, Tuple, List

from config import (
    PROFILES,
    PROFILE_THRESHOLD,
    PROFILE_THRESHOLDS,
    PROFILE_THRESHOLD_METHOD,
    PROFILE_PRIORITY,
)


def reverse_score(value):
    """معکوس‌سازی گویه‌های 5 گزینه‌ای."""
    if value is None:
        return None

    try:
        return 6 - float(value)
    except (TypeError, ValueError):
        return None


def _get_item_value(row: Dict[str, Any], item: str):
    """
    دریافت مقدار گویه با پشتیبانی از حروف بزرگ/کوچک.

    مثال:
        Q3  -> q3
        Q20R -> q20 سپس reverse score
    """

    if not isinstance(row, dict):
        return None

    item = str(item).strip()

    # گویه معکوس
    if item.upper().endswith("R"):
        base = item[:-1].strip().lower()
        value = row.get(base)

        # در صورت وجود کلید با حروف بزرگ
        if value is None:
            value = row.get(base.upper())

        return reverse_score(value) if value is not None else None

    # گویه عادی
    key = item.lower()
    value = row.get(key)

    # سازگاری با داده‌هایی که کلید بزرگ دارند
    if value is None:
        value = row.get(item.upper())

    return value


def calculate_profile_scores(row: Dict[str, Any]) -> Dict[str, float]:
    """محاسبه امتیاز 10 پروفایل عملیاتی."""

    scores = {}

    for profile_key, profile in PROFILES.items():
        values = []

        for item in profile["items"]:
            value = _get_item_value(row, item)

            if value is not None:
                try:
                    values.append(float(value))
                except (TypeError, ValueError):
                    pass

        scores[profile_key] = (
            round(sum(values) / len(values), 3)
            if values
            else None
        )

    return scores


def classify_profile_score(
    score: float,
    profile_key: str = None
) -> str:
    """
    طبقه‌بندی امتیاز یک پروفایل به سه سطح عملیاتی.

    اگر profile_key مشخص باشد، از آستانه همان پروفایل استفاده می‌شود.
    """

    if score is None:
        return "unknown"

    try:
        value = float(score)
    except (TypeError, ValueError):
        return "unknown"

    thresholds = PROFILE_THRESHOLDS.get(profile_key)

    if thresholds is None:
        # سازگاری با فراخوانی‌های قدیمی
        if value <= PROFILE_THRESHOLD["low"]:
            return "low"

        if value <= PROFILE_THRESHOLD["medium"]:
            return "medium"

        return "high"

    if value <= thresholds["low_max"]:
        return "low"

    if value <= thresholds["medium_max"]:
        return "medium"

    return "high"


def get_profile_levels(
    profile_scores: Dict[str, float]
) -> Dict[str, str]:

    return {
        key: classify_profile_score(
            score,
            profile_key=key
        )
        for key, score in profile_scores.items()
    }


def get_dominant_profiles(
    profile_scores: Dict[str, float],
    max_profiles: int = 2,
) -> List[Tuple[str, float]]:
    """
    انتخاب حداکثر دو پروفایل برجسته.

    پروفایل‌های low حذف می‌شوند.
    سپس بر اساس امتیاز نزولی مرتب می‌شوند.
    """

    candidates = [
        (key, score)
        for key, score in profile_scores.items()
        if (
            score is not None
            and classify_profile_score(
                score,
                profile_key=key
            ) != "low"
        )
    ]

    priority_index = {
        key: i
        for i, key in enumerate(PROFILE_PRIORITY)
    }

    candidates.sort(
        key=lambda x: (
            -x[1],
            priority_index.get(x[0], 999)
        )
    )

    return candidates[:max_profiles]


def get_dominant_profile(row: Dict[str, Any]):
    scores = calculate_profile_scores(row)

    dominant = get_dominant_profiles(
        scores,
        max_profiles=1
    )

    return (
        dominant[0][0] if dominant else None,
        scores
    )


def create_profile(
    row: Dict[str, Any]
) -> Dict[str, Any]:

    scores = calculate_profile_scores(row)

    levels = get_profile_levels(scores)

    dominant = get_dominant_profiles(
        scores,
        max_profiles=2
    )

    return {
        "scores": scores,
        "levels": levels,
        "dominant_profiles": dominant,
        "dominant_profile": (
            dominant[0][0]
            if dominant
            else None
        ),
        "thresholds": PROFILE_THRESHOLDS,
        "threshold_method": PROFILE_THRESHOLD_METHOD,
    }