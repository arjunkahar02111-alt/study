"""
Unified Storage Facade for SYNTRIQ.
Routes authenticated user requests to Cloud Firestore (using the user's own
Firebase ID Token so Firestore Security Rules enforce UID isolation), or to
UID-isolated SQLite when running offline / in automated local tests.
"""

from datetime import date
from typing import Any, Dict, List, Optional

import database
import firebase_auth
import firestore_store


def _use_firestore(user: Optional[Dict[str, Any]]) -> bool:
    return bool(
        user
        and user.get("id_token")
        and firebase_auth.is_firebase_configured()
    )


def ensure_user_workspace(user: Dict[str, Any], db_path: str) -> bool:
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.ensure_user_workspace(uid, user["id_token"], user)
    return database.upsert_user_profile(
        uid=uid,
        email=user.get("email", ""),
        display_name=user.get("name", ""),
        photo_url=user.get("picture", ""),
        db_path=db_path,
    )


def get_user_settings(user: Dict[str, Any], db_path: str) -> Dict[str, Any]:
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.get_user_settings(uid, user["id_token"])
    return database.get_user_settings(uid, db_path=db_path)


def update_user_settings(
    user: Dict[str, Any],
    db_path: str,
    max_safe_hours: float,
    default_focus_minutes: int,
    sound_effects_enabled: bool,
) -> Dict[str, Any]:
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.update_user_settings(
            uid, user["id_token"], max_safe_hours, default_focus_minutes, sound_effects_enabled
        )
    return database.update_user_settings(
        uid, max_safe_hours, default_focus_minutes, sound_effects_enabled, db_path=db_path
    )


def add_task(
    user: Dict[str, Any],
    db_path: str,
    title: str,
    subject: str,
    deadline: str,
    difficulty: int,
    importance: int,
    estimated_hours: Optional[float] = None,
    status: str = "Pending",
):
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.add_task(
            uid, user["id_token"], title, subject, deadline, difficulty, importance, estimated_hours, status
        )
    return database.add_task(
        title=title,
        subject=subject,
        deadline=deadline,
        difficulty=difficulty,
        importance=importance,
        estimated_hours=estimated_hours,
        status=status,
        db_path=db_path,
        user_uid=uid,
    )


def get_task_by_id(user: Dict[str, Any], db_path: str, task_id: Any) -> Optional[Dict[str, Any]]:
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.get_task_by_id(uid, user["id_token"], str(task_id))
    try:
        tid = int(task_id)
    except (ValueError, TypeError):
        return None
    return database.get_task_by_id(tid, db_path=db_path, user_uid=uid)


def get_all_tasks(user: Dict[str, Any], db_path: str) -> List[Dict[str, Any]]:
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.get_all_tasks(uid, user["id_token"])
    return database.get_all_tasks(db_path=db_path, user_uid=uid)


def get_pending_tasks(user: Dict[str, Any], db_path: str) -> List[Dict[str, Any]]:
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.get_pending_tasks(uid, user["id_token"])
    return database.get_pending_tasks(db_path=db_path, user_uid=uid)


def get_completed_tasks(user: Dict[str, Any], db_path: str) -> List[Dict[str, Any]]:
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.get_completed_tasks(uid, user["id_token"])
    return database.get_completed_tasks(db_path=db_path, user_uid=uid)


def get_overdue_tasks(user: Dict[str, Any], db_path: str) -> List[Dict[str, Any]]:
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.get_overdue_tasks(uid, user["id_token"])
    return database.get_overdue_tasks(db_path=db_path, user_uid=uid)


def get_upcoming_tasks(user: Dict[str, Any], db_path: str, days_ahead: int = 7) -> List[Dict[str, Any]]:
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.get_upcoming_tasks(uid, user["id_token"], days_ahead=days_ahead)
    return database.get_upcoming_tasks(days_ahead=days_ahead, db_path=db_path, user_uid=uid)


def get_study_plan(user: Dict[str, Any], db_path: str) -> List[Dict[str, Any]]:
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.get_study_plan(uid, user["id_token"])
    return database.get_study_plan(db_path=db_path, user_uid=uid)


def update_task(
    user: Dict[str, Any],
    db_path: str,
    task_id: Any,
    title: str,
    subject: str,
    deadline: str,
    difficulty: int,
    importance: int,
    estimated_hours: Optional[float] = None,
    status: Optional[str] = None,
) -> bool:
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.update_task(
            uid, user["id_token"], str(task_id), title, subject, deadline, difficulty, importance, estimated_hours, status
        )
    try:
        tid = int(task_id)
    except (ValueError, TypeError):
        return False
    return database.update_task(
        task_id=tid,
        title=title,
        subject=subject,
        deadline=deadline,
        difficulty=difficulty,
        importance=importance,
        estimated_hours=estimated_hours,
        status=status,
        db_path=db_path,
        user_uid=uid,
    )


def delete_task(user: Dict[str, Any], db_path: str, task_id: Any) -> bool:
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.delete_task(uid, user["id_token"], str(task_id))
    try:
        tid = int(task_id)
    except (ValueError, TypeError):
        return False
    return database.delete_task(tid, db_path=db_path, user_uid=uid)


def complete_task(user: Dict[str, Any], db_path: str, task_id: Any) -> bool:
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.complete_task(uid, user["id_token"], str(task_id))
    try:
        tid = int(task_id)
    except (ValueError, TypeError):
        return False
    return database.complete_task(tid, db_path=db_path, user_uid=uid)


def clear_all_tasks(user: Dict[str, Any], db_path: str) -> None:
    uid = user["uid"]
    if _use_firestore(user):
        firestore_store.clear_all_tasks(uid, user["id_token"])
        return
    database.clear_all_tasks(db_path=db_path, user_uid=uid)


def add_subtask(user: Dict[str, Any], db_path: str, task_id: Any, title: str):
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.add_subtask(uid, user["id_token"], str(task_id), title)
    return database.add_subtask(int(task_id), title, db_path=db_path, user_uid=uid)


def toggle_subtask(user: Dict[str, Any], db_path: str, subtask_id: Any) -> bool:
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.toggle_subtask(uid, user["id_token"], str(subtask_id))
    try:
        sid = int(subtask_id)
    except (ValueError, TypeError):
        return False
    return database.toggle_subtask(sid, db_path=db_path, user_uid=uid)


def delete_subtask(user: Dict[str, Any], db_path: str, subtask_id: Any) -> bool:
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.delete_subtask(uid, user["id_token"], str(subtask_id))
    try:
        sid = int(subtask_id)
    except (ValueError, TypeError):
        return False
    return database.delete_subtask(sid, db_path=db_path, user_uid=uid)


def get_routines(user: Dict[str, Any], db_path: str) -> List[Dict[str, Any]]:
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.get_routines(uid, user["id_token"])
    return database.get_routines(uid, db_path=db_path)


def add_routine(
    user: Dict[str, Any],
    db_path: str,
    title: str,
    subject: str,
    day_of_week: str,
    start_time: str,
    end_time: str,
    focus_goal: str = "",
):
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.add_routine(
            uid, user["id_token"], title, subject, day_of_week, start_time, end_time, focus_goal
        )
    return database.add_routine(
        uid, title, subject, day_of_week, start_time, end_time, focus_goal, db_path=db_path
    )


def toggle_routine(user: Dict[str, Any], db_path: str, routine_id: Any) -> bool:
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.toggle_routine(uid, user["id_token"], str(routine_id))
    try:
        rid = int(routine_id)
    except (ValueError, TypeError):
        return False
    return database.toggle_routine(uid, rid, db_path=db_path)


def delete_routine(user: Dict[str, Any], db_path: str, routine_id: Any) -> bool:
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.delete_routine(uid, user["id_token"], str(routine_id))
    try:
        rid = int(routine_id)
    except (ValueError, TypeError):
        return False
    return database.delete_routine(uid, rid, db_path=db_path)


def get_active_session(user: Dict[str, Any], db_path: str) -> Optional[Dict[str, Any]]:
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.get_active_session(uid, user["id_token"])
    return database.get_active_session(db_path=db_path, user_uid=uid)


def start_tracking_session(user: Dict[str, Any], db_path: str, task_id: Any, force: bool = False) -> Dict[str, Any]:
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.start_tracking_session(uid, user["id_token"], str(task_id), force=force)
    return database.start_tracking_session(int(task_id), force=force, db_path=db_path, user_uid=uid)


def pause_tracking_session(user: Dict[str, Any], db_path: str) -> Optional[Dict[str, Any]]:
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.pause_tracking_session(uid, user["id_token"])
    return database.pause_tracking_session(db_path=db_path, user_uid=uid)


def resume_tracking_session(user: Dict[str, Any], db_path: str) -> Optional[Dict[str, Any]]:
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.resume_tracking_session(uid, user["id_token"])
    return database.resume_tracking_session(db_path=db_path, user_uid=uid)


def stop_tracking_session(user: Dict[str, Any], db_path: str) -> Dict[str, Any]:
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.stop_tracking_session(uid, user["id_token"])
    return database.stop_tracking_session(db_path=db_path, user_uid=uid)


def log_study_session(user: Dict[str, Any], db_path: str, task_id: Optional[Any], minutes: int):
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.log_study_session(uid, user["id_token"], str(task_id) if task_id else None, minutes)
    tid = int(task_id) if task_id else None
    return database.log_study_session(tid, minutes, db_path=db_path, user_uid=uid)


def get_task_sessions(user: Dict[str, Any], db_path: str, task_id: Any) -> List[Dict[str, Any]]:
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.get_task_sessions(uid, user["id_token"], str(task_id))
    return database.get_task_sessions(int(task_id), db_path=db_path, user_uid=uid)


def get_study_streak(user: Dict[str, Any], db_path: str) -> int:
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.get_study_streak(uid, user["id_token"])
    return database.get_study_streak(db_path=db_path, user_uid=uid)


def get_weekly_workload_heatmap(user: Dict[str, Any], db_path: str) -> List[Dict[str, Any]]:
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.get_weekly_workload_heatmap(uid, user["id_token"])
    return database.get_weekly_workload_heatmap(db_path=db_path, user_uid=uid)


def get_daily_capacity(user: Dict[str, Any], db_path: str, max_safe_hours: float = 6.0) -> Dict[str, Any]:
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.get_daily_capacity(uid, user["id_token"], max_safe_hours=max_safe_hours)
    return database.get_daily_capacity(db_path=db_path, max_safe_hours=max_safe_hours, user_uid=uid)


def get_time_intelligence_data(user: Dict[str, Any], db_path: str) -> Dict[str, Any]:
    uid = user["uid"]
    if _use_firestore(user):
        return firestore_store.get_time_intelligence_data(uid, user["id_token"])
    return database.get_time_intelligence_data(db_path=db_path, user_uid=uid)
