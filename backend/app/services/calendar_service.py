from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend.app.models import StudyTask


def get_calendar_tasks(
    db: Session,
    user_id: str,
    month: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    is_completed: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Retrieves study calendar tasks for a user, optionally filtered by month or date range,
    category, or completion status. Also computes completion rate summary.
    """
    query = db.query(StudyTask).filter(StudyTask.user_id == user_id)

    if month:
        # e.g., "2026-11" -> match tasks in that month
        query = query.filter(StudyTask.task_date.startswith(month.strip()))
    if start_date:
        query = query.filter(StudyTask.task_date >= start_date.strip())
    if end_date:
        query = query.filter(StudyTask.task_date <= end_date.strip())
    if category and category.lower() != "all":
        query = query.filter(StudyTask.category.ilike(f"%{category.strip()}%"))
    if is_completed is not None:
        query = query.filter(StudyTask.is_completed == is_completed)

    tasks = query.order_by(StudyTask.task_date.asc(), StudyTask.start_time.asc()).all()

    total = len(tasks)
    completed = sum(1 for t in tasks if t.is_completed)
    pending = total - completed
    rate = round((completed / total) * 100, 1) if total > 0 else 0.0

    return {
        "tasks": [t.to_dict() for t in tasks],
        "summary": {
            "total_tasks": total,
            "completed_tasks": completed,
            "pending_tasks": pending,
            "completion_rate": rate,
        },
    }


def create_calendar_task(
    db: Session,
    user_id: str,
    title: str,
    task_date: str,
    category: str = "General",
    description: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    priority: str = "medium",
) -> StudyTask:
    """
    Creates a new study schedule task in Neon PostgreSQL.
    """
    task = StudyTask(
        user_id=user_id.strip(),
        title=title.strip(),
        description=description.strip() if description else None,
        category=category.strip() if category else "General",
        task_date=task_date.strip()[:10],
        start_time=start_time.strip() if start_time else None,
        end_time=end_time.strip() if end_time else None,
        priority=priority.strip().lower() if priority else "medium",
        is_completed=False,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_calendar_task(
    db: Session,
    user_id: str,
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    category: Optional[str] = None,
    task_date: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    priority: Optional[str] = None,
    is_completed: Optional[bool] = None,
) -> Optional[StudyTask]:
    """
    Updates an existing calendar task.
    """
    task = db.query(StudyTask).filter(
        StudyTask.id == task_id,
        StudyTask.user_id == user_id,
    ).first()

    if not task:
        return None

    if title is not None:
        task.title = title.strip()
    if description is not None:
        task.description = description.strip() if description else None
    if category is not None:
        task.category = category.strip()
    if task_date is not None:
        task.task_date = task_date.strip()[:10]
    if start_time is not None:
        task.start_time = start_time.strip() if start_time else None
    if end_time is not None:
        task.end_time = end_time.strip() if end_time else None
    if priority is not None:
        task.priority = priority.strip().lower()
    if is_completed is not None:
        task.is_completed = is_completed

    db.commit()
    db.refresh(task)
    return task


def toggle_task_completion(db: Session, user_id: str, task_id: int) -> Optional[StudyTask]:
    """
    Toggles the is_completed boolean on a study task.
    """
    task = db.query(StudyTask).filter(
        StudyTask.id == task_id,
        StudyTask.user_id == user_id,
    ).first()

    if not task:
        return None

    task.is_completed = not task.is_completed
    db.commit()
    db.refresh(task)
    return task


def delete_calendar_task(db: Session, user_id: str, task_id: int) -> bool:
    """
    Deletes a calendar task.
    """
    task = db.query(StudyTask).filter(
        StudyTask.id == task_id,
        StudyTask.user_id == user_id,
    ).first()

    if not task:
        return False

    db.delete(task)
    db.commit()
    return True

