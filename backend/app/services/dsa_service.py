from datetime import datetime, date, timedelta, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.models import DSAActivity


def log_dsa_problem(
    db: Session,
    user_id: str,
    problem_title: str,
    platform: str = "LeetCode",
    difficulty: str = "Medium",
    topic: str = "Arrays",
    activity_date: Optional[str] = None,
    problem_url: Optional[str] = None,
    notes: Optional[str] = None,
) -> DSAActivity:
    """
    Logs a solved DSA problem for the user into Neon PostgreSQL.
    """
    if not activity_date:
        activity_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Clean date format
    activity_date = activity_date.strip()[:10]

    record = DSAActivity(
        user_id=user_id.strip(),
        problem_title=problem_title.strip(),
        platform=platform.strip() if platform else "LeetCode",
        difficulty=difficulty.strip() if difficulty else "Medium",
        topic=topic.strip() if topic else "Arrays",
        activity_date=activity_date,
        problem_url=problem_url.strip() if problem_url else None,
        notes=notes.strip() if notes else None,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_dsa_heatmap_data(
    db: Session,
    user_id: str,
    days_span: int = 365,
) -> Dict[str, Any]:
    """
    Calculates LeetCode/GitHub-style green activity grid for the user
    over the trailing `days_span` days, along with streaks, breakdown, and recent problems.
    """
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=days_span - 1)
    start_date_str = start_date.strftime("%Y-%m-%d")

    # Fetch all activities for user
    all_activities = (
        db.query(DSAActivity)
        .filter(DSAActivity.user_id == user_id)
        .order_by(DSAActivity.activity_date.asc(), DSAActivity.id.asc())
        .all()
    )

    # Aggregations
    date_counts: Dict[str, int] = {}
    difficulty_counts: Dict[str, int] = {"Easy": 0, "Medium": 0, "Hard": 0}
    platform_counts: Dict[str, int] = {}
    topic_counts: Dict[str, int] = {}

    for act in all_activities:
        d_str = act.activity_date
        date_counts[d_str] = date_counts.get(d_str, 0) + 1

        # Difficulty
        diff = act.difficulty or "Medium"
        if diff in difficulty_counts:
            difficulty_counts[diff] += 1
        else:
            difficulty_counts[diff] = 1

        # Platform
        plat = act.platform or "LeetCode"
        platform_counts[plat] = platform_counts.get(plat, 0) + 1

        # Topic
        top = act.topic or "Arrays"
        topic_counts[top] = topic_counts.get(top, 0) + 1

    # Generate full 365-day grid
    heatmap_days: List[Dict[str, Any]] = []
    curr_date = start_date
    while curr_date <= today:
        d_str = curr_date.strftime("%Y-%m-%d")
        count = date_counts.get(d_str, 0)

        # Intensity level (0 to 4)
        if count == 0:
            level = 0
        elif count <= 2:
            level = 1
        elif count <= 4:
            level = 2
        elif count <= 6:
            level = 3
        else:
            level = 4

        heatmap_days.append({
            "date": d_str,
            "count": count,
            "problem_count": count,
            "level": level,
            "intensity": level,
            "day_of_week": curr_date.weekday(),  # 0=Monday, 6=Sunday
        })
        curr_date += timedelta(days=1)

    # Calculate streaks
    sorted_active_dates = sorted([datetime.strptime(d, "%Y-%m-%d").date() for d in date_counts.keys()])

    # Current streak
    current_streak = 0
    check_date = today
    if check_date not in sorted_active_dates:
        # Check if yesterday had activity
        yesterday = today - timedelta(days=1)
        if yesterday in sorted_active_dates:
            check_date = yesterday

    if check_date in sorted_active_dates:
        while check_date in sorted_active_dates:
            current_streak += 1
            check_date -= timedelta(days=1)

    # Max streak
    max_streak = 0
    if sorted_active_dates:
        temp_streak = 1
        max_streak = 1
        for i in range(1, len(sorted_active_dates)):
            if sorted_active_dates[i] == sorted_active_dates[i - 1] + timedelta(days=1):
                temp_streak += 1
                if temp_streak > max_streak:
                    max_streak = temp_streak
            else:
                temp_streak = 1

    # Recent 25 problems
    recent_records = (
        db.query(DSAActivity)
        .filter(DSAActivity.user_id == user_id)
        .order_by(DSAActivity.activity_date.desc(), DSAActivity.id.desc())
        .limit(25)
        .all()
    )

    return {
        "user_id": user_id,
        "total_problems": len(all_activities),
        "current_streak": current_streak,
        "max_streak": max_streak,
        "active_days_count": len(date_counts),
        "difficulty_breakdown": difficulty_counts,
        "platform_breakdown": platform_counts,
        "topic_breakdown": dict(sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:8]),
        "heatmap_days": heatmap_days,
        "days": heatmap_days,
        "recent_problems": [r.to_dict() for r in recent_records],
    }


def get_recent_dsa_problems(db: Session, user_id: str, limit: int = 30) -> List[Dict[str, Any]]:
    """Returns the list of recently logged problems for a user."""
    records = (
        db.query(DSAActivity)
        .filter(DSAActivity.user_id == user_id)
        .order_by(DSAActivity.activity_date.desc(), DSAActivity.id.desc())
        .limit(limit)
        .all()
    )
    return [r.to_dict() for r in records]


def delete_dsa_problem(db: Session, user_id: str, activity_id: int) -> bool:
    """Deletes a DSA problem record belonging to the user."""
    rec = db.query(DSAActivity).filter(
        DSAActivity.id == activity_id,
        DSAActivity.user_id == user_id,
    ).first()
    if not rec:
        return False
    db.delete(rec)
    db.commit()
    return True
