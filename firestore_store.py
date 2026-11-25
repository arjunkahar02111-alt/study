"""
Cloud Firestore REST Store for SYNTRIQ.
Executes all user data operations under users/{uid}/... using the
authenticated user's Firebase ID Token (Authorization: Bearer <id_token>),
so Firestore Security Rules enforce UID isolation on every request.
"""

import os
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union

import requests

from priority_calculator import (
    calculate_priority,
    calculate_urgency,
    calculate_workload,
    days_remaining,
    is_overdue,
    parse_date,
)

FIRESTORE_API_BASE = "https://firestore.googleapis.com/v1"


class FirestorePermissionError(PermissionError):
    """Raised when Firestore rejects a request due to Security Rules (401/403)."""


def _project_id() -> str:
    pid = os.environ.get("FIREBASE_PROJECT_ID", "").strip()
    if pid:
        return pid
    import firebase_auth
    return firebase_auth.get_firebase_web_config().get("projectId", "")


def _base_docs_url(project_id: Optional[str] = None) -> str:
    pid = project_id or _project_id()
    if not pid:
        raise ValueError("FIREBASE_PROJECT_ID is not configured.")
    db_id = os.environ.get("FIRESTORE_DATABASE_ID", "(default)").strip() or "(default)"
    return f"{FIRESTORE_API_BASE}/projects/{pid}/databases/{db_id}/documents"


def _headers(id_token: str) -> Dict[str, str]:
    if not id_token:
        raise FirestorePermissionError("Missing Firebase ID token for Firestore access.")
    import firebase_auth
    api_key = firebase_auth.get_firebase_web_config().get("apiKey", "")
    hdrs = {
        "Authorization": f"Bearer {id_token}",
        "Content-Type": "application/json",
    }
    if api_key:
        hdrs["x-goog-api-key"] = api_key
    return hdrs


def _encode_value(val: Any) -> Dict[str, Any]:
    if val is None:
        return {"nullValue": None}
    if isinstance(val, bool):
        return {"booleanValue": val}
    if isinstance(val, int):
        return {"integerValue": str(val)}
    if isinstance(val, float):
        return {"doubleValue": val}
    if isinstance(val, str):
        return {"stringValue": val}
    if isinstance(val, list):
        return {"arrayValue": {"values": [_encode_value(v) for v in val]}}
    if isinstance(val, dict):
        return {"mapValue": {"fields": {str(k): _encode_value(v) for k, v in val.items()}}}
    return {"stringValue": str(val)}


def _decode_value(val_obj: Dict[str, Any]) -> Any:
    if "nullValue" in val_obj:
        return None
    if "booleanValue" in val_obj:
        return bool(val_obj["booleanValue"])
    if "integerValue" in val_obj:
        return int(val_obj["integerValue"])
    if "doubleValue" in val_obj:
        return float(val_obj["doubleValue"])
    if "stringValue" in val_obj:
        return val_obj["stringValue"]
    if "timestampValue" in val_obj:
        return val_obj["timestampValue"]
    if "arrayValue" in val_obj:
        return [_decode_value(v) for v in val_obj["arrayValue"].get("values", [])]
    if "mapValue" in val_obj:
        return {k: _decode_value(v) for k, v in val_obj["mapValue"].get("fields", {}).items()}
    return None


def _encode_doc(data: Dict[str, Any]) -> Dict[str, Any]:
    return {"fields": {str(k): _encode_value(v) for k, v in data.items()}}


def _decode_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    fields = doc.get("fields", {})
    parsed = {k: _decode_value(v) for k, v in fields.items()}
    name = doc.get("name", "")
    if name:
        parsed["_doc_id"] = name.rsplit("/", 1)[-1]
    return parsed


def _handle_response(resp: requests.Response) -> Dict[str, Any]:
    if resp.status_code in (401, 403):
        body = resp.text or ""
        if "Permission denied on the service" in body or "SERVICE_DISABLED" in body or "has not been used in project" in body:
            pid = _project_id() or "study-planner-b8fe1"
            raise FirestorePermissionError(
                f"Cloud Firestore is not enabled yet on Firebase project '{pid}'. "
                f"Open Firebase Console -> Build -> Firestore Database -> Create database (Production mode), "
                f"then paste firestore.rules into the Rules tab and click Publish."
            )
        raise FirestorePermissionError(f"Firestore access denied ({resp.status_code}): {body}")
    if resp.status_code == 404:
        return {}
    if not resp.ok:
        raise RuntimeError(f"Firestore error ({resp.status_code}): {resp.text}")
    return resp.json() if resp.text else {}


def _get_doc(uid: str, rel_path: str, id_token: str) -> Optional[Dict[str, Any]]:
    url = f"{_base_docs_url()}/users/{uid}/{rel_path}"
    resp = requests.get(url, headers=_headers(id_token), timeout=10)
    if resp.status_code == 404:
        return None
    data = _handle_response(resp)
    return _decode_doc(data) if data else None


def _set_doc(uid: str, rel_path: str, data: Dict[str, Any], id_token: str) -> Dict[str, Any]:
    url = f"{_base_docs_url()}/users/{uid}/{rel_path}"
    payload = dict(data)
    payload["ownerUid"] = uid
    resp = requests.patch(url, headers=_headers(id_token), json=_encode_doc(payload), timeout=10)
    res = _handle_response(resp)
    return _decode_doc(res) if res else payload


def _delete_doc(uid: str, rel_path: str, id_token: str) -> bool:
    url = f"{_base_docs_url()}/users/{uid}/{rel_path}"
    resp = requests.delete(url, headers=_headers(id_token), timeout=10)
    if resp.status_code == 404:
        return False
    _handle_response(resp)
    return True


def _list_collection(uid: str, collection_name: str, id_token: str, page_size: int = 200) -> List[Dict[str, Any]]:
    url = f"{_base_docs_url()}/users/{uid}/{collection_name}"
    items: List[Dict[str, Any]] = []
    next_token = None
    while True:
        params: Dict[str, Any] = {"pageSize": page_size}
        if next_token:
            params["pageToken"] = next_token
        resp = requests.get(url, headers=_headers(id_token), params=params, timeout=10)
        if resp.status_code == 404:
            return []
        data = _handle_response(resp)
        for doc in data.get("documents", []):
            items.append(_decode_doc(doc))
        next_token = data.get("nextPageToken")
        if not next_token:
            break
    return items


def format_duration(seconds: Union[int, float, None]) -> str:
    if not seconds or seconds <= 0:
        return "0m"
    sec_int = int(seconds)
    m, s = divmod(sec_int, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}h {m}m" if m > 0 else f"{h}h"
    if m > 0:
        return f"{m}m {s}s" if s > 0 else f"{m}m"
    return f"{s}s"


def _format_task_dict(task: Dict[str, Any], current_date: date = None) -> Dict[str, Any]:
    if current_date is None:
        current_date = date.today()

    task_id = task.get("Task_ID") or task.get("_doc_id")
    task["Task_ID"] = str(task_id)

    deadline_val = task["Task_Deadline"]
    overdue = is_overdue(deadline_val, current_date)
    days_left = days_remaining(deadline_val, current_date)
    urgency_val = calculate_urgency(deadline_val, current_date)
    workload_val = calculate_workload(task.get("Estimated_Hours") or task.get("Target_Hours"))

    task["is_overdue"] = overdue
    task["days_remaining"] = days_left
    task["urgency"] = urgency_val
    task["workload"] = workload_val

    tracked_sec = int(task.get("Total_Tracked_Seconds") or 0)
    task["total_tracked_seconds"] = tracked_sec
    task["tracked_time_formatted"] = format_duration(tracked_sec) if tracked_sec > 0 else "0m"

    if task.get("Completed_At") and task.get("First_Tracked_At"):
        try:
            start_dt = datetime.fromisoformat(task["First_Tracked_At"])
            comp_dt = datetime.fromisoformat(task["Completed_At"])
            cal_delta = comp_dt - start_dt
            cal_days = cal_delta.days
            cal_hours = cal_delta.seconds // 3600
            task["calendar_span_formatted"] = f"{cal_days}d {cal_hours}h" if cal_days > 0 else f"{max(1, cal_hours)}h"
        except Exception:
            task["calendar_span_formatted"] = None
    else:
        task["calendar_span_formatted"] = None

    score = float(task.get("Priority_Score") or 1.0)
    task["Priority_Score"] = score
    if score >= 4.0:
        task["priority_category"] = "Urgent / High"
        task["badge_class"] = "badge-danger"
    elif score >= 3.0:
        task["priority_category"] = "Moderate"
        task["badge_class"] = "badge-warning"
    else:
        task["priority_category"] = "Low"
        task["badge_class"] = "badge-info"

    subs = task.get("subtasks") or []
    normalized_subs = []
    for s in subs:
        normalized_subs.append({
            "Subtask_ID": str(s.get("Subtask_ID") or s.get("id") or ""),
            "Task_ID": str(task["Task_ID"]),
            "Subtask_Title": s.get("Subtask_Title") or s.get("title") or "",
            "Is_Completed": 1 if s.get("Is_Completed") else 0,
        })
    task["subtasks"] = normalized_subs
    return task


# =============================================================================
# User Profile & Settings
# =============================================================================

def ensure_user_workspace(uid: str, id_token: str, user_claims: Dict[str, Any]) -> bool:
    """
    Creates the user's Firestore profile and default settings if first login.
    Returns True if this is a brand-new user workspace.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    existing = _get_doc(uid, "profile/main", id_token)
    is_new = existing is None

    profile_payload = {
        "uid": uid,
        "ownerUid": uid,
        "email": user_claims.get("email", ""),
        "displayName": user_claims.get("name", ""),
        "photoURL": user_claims.get("picture", ""),
        "lastLoginAt": now_iso,
        "createdAt": existing.get("createdAt", now_iso) if existing else now_iso,
    }
    _set_doc(uid, "profile/main", profile_payload, id_token)

    settings_doc = _get_doc(uid, "settings/preferences", id_token)
    if settings_doc is None:
        _set_doc(
            uid,
            "settings/preferences",
            {
                "ownerUid": uid,
                "maxSafeHours": 6.0,
                "defaultFocusMinutes": 25,
                "soundEffectsEnabled": True,
                "updatedAt": now_iso,
            },
            id_token,
        )
    return is_new


def get_user_settings(uid: str, id_token: str) -> Dict[str, Any]:
    doc = _get_doc(uid, "settings/preferences", id_token)
    if not doc:
        return {"maxSafeHours": 6.0, "defaultFocusMinutes": 25, "soundEffectsEnabled": True}
    return {
        "maxSafeHours": float(doc.get("maxSafeHours", 6.0)),
        "defaultFocusMinutes": int(doc.get("defaultFocusMinutes", 25)),
        "soundEffectsEnabled": bool(doc.get("soundEffectsEnabled", True)),
    }


def update_user_settings(
    uid: str,
    id_token: str,
    max_safe_hours: float = 6.0,
    default_focus_minutes: int = 25,
    sound_effects_enabled: bool = True,
) -> Dict[str, Any]:
    payload = {
        "ownerUid": uid,
        "maxSafeHours": max(1.0, min(16.0, float(max_safe_hours))),
        "defaultFocusMinutes": int(default_focus_minutes) if int(default_focus_minutes) in (15, 25, 45, 50) else 25,
        "soundEffectsEnabled": bool(sound_effects_enabled),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }
    _set_doc(uid, "settings/preferences", payload, id_token)
    return payload


# =============================================================================
# Tasks CRUD & Priority Plan
# =============================================================================

def add_task(
    uid: str,
    id_token: str,
    title: str,
    subject: str,
    deadline: str,
    difficulty: int,
    importance: int,
    estimated_hours: Optional[float] = None,
    status: str = "Pending",
) -> str:
    title = (title or "").strip()
    subject = (subject or "").strip()
    deadline_str = (deadline or "").strip()
    if not title or not subject or not deadline_str:
        raise ValueError("Please complete all required fields")

    parsed_deadline = parse_date(deadline_str)
    formatted_deadline = parsed_deadline.strftime("%Y-%m-%d")
    diff_val = int(difficulty)
    imp_val = int(importance)
    if not (1 <= diff_val <= 5) or not (1 <= imp_val <= 5):
        raise ValueError("Invalid input")

    hours_val = None
    if estimated_hours is not None and estimated_hours != "":
        val = float(estimated_hours)
        if val <= 0:
            raise ValueError("Invalid input")
        hours_val = val

    priority_score = calculate_priority(formatted_deadline, diff_val, imp_val, hours_val)
    task_id = f"{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    payload = {
        "ownerUid": uid,
        "Task_ID": task_id,
        "Task_Title": title,
        "Task_Subject": subject,
        "Task_Deadline": formatted_deadline,
        "Task_Difficulty": diff_val,
        "Task_Importance": imp_val,
        "Estimated_Hours": hours_val,
        "Target_Hours": hours_val,
        "Total_Tracked_Seconds": 0,
        "Priority_Score": priority_score,
        "Task_Status": status if status in ("Pending", "Completed") else "Pending",
        "First_Tracked_At": None,
        "Completed_At": None,
        "subtasks": [],
        "createdAt": now_iso,
        "updatedAt": now_iso,
    }
    _set_doc(uid, f"tasks/{task_id}", payload, id_token)
    return task_id


def get_task_by_id(uid: str, id_token: str, task_id: str) -> Optional[Dict[str, Any]]:
    doc = _get_doc(uid, f"tasks/{task_id}", id_token)
    if not doc or doc.get("ownerUid") != uid:
        return None
    return _format_task_dict(doc)


def get_all_tasks(uid: str, id_token: str, current_date: date = None) -> List[Dict[str, Any]]:
    docs = _list_collection(uid, "tasks", id_token)
    tasks = [_format_task_dict(d, current_date) for d in docs if d.get("ownerUid", uid) == uid]
    tasks.sort(key=lambda t: (t["Task_Deadline"], -t["Priority_Score"]))
    return tasks


def get_pending_tasks(uid: str, id_token: str, current_date: date = None) -> List[Dict[str, Any]]:
    return [t for t in get_all_tasks(uid, id_token, current_date) if t["Task_Status"] == "Pending"]


def get_completed_tasks(uid: str, id_token: str, current_date: date = None) -> List[Dict[str, Any]]:
    tasks = [t for t in get_all_tasks(uid, id_token, current_date) if t["Task_Status"] == "Completed"]
    tasks.sort(key=lambda t: t["Task_Deadline"], reverse=True)
    return tasks


def get_overdue_tasks(uid: str, id_token: str, current_date: date = None) -> List[Dict[str, Any]]:
    if current_date is None:
        current_date = date.today()
    today_str = current_date.strftime("%Y-%m-%d")
    return [t for t in get_pending_tasks(uid, id_token, current_date) if t["Task_Deadline"] < today_str]


def get_upcoming_tasks(uid: str, id_token: str, days_ahead: int = 7, current_date: date = None) -> List[Dict[str, Any]]:
    if current_date is None:
        current_date = date.today()
    today_str = current_date.strftime("%Y-%m-%d")
    max_str = (current_date + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    return [
        t for t in get_pending_tasks(uid, id_token, current_date)
        if today_str <= t["Task_Deadline"] <= max_str
    ]


def get_study_plan(uid: str, id_token: str, current_date: date = None) -> List[Dict[str, Any]]:
    if current_date is None:
        current_date = date.today()
    pending = get_pending_tasks(uid, id_token, current_date)
    for task in pending:
        score = calculate_priority(
            task["Task_Deadline"],
            task["Task_Difficulty"],
            task["Task_Importance"],
            task.get("Estimated_Hours"),
            current_date=current_date,
        )
        if abs(score - float(task["Priority_Score"])) > 0.001:
            task["Priority_Score"] = score
            raw = _get_doc(uid, f"tasks/{task['Task_ID']}", id_token)
            if raw:
                raw["Priority_Score"] = score
                raw["updatedAt"] = datetime.now(timezone.utc).isoformat()
                _set_doc(uid, f"tasks/{task['Task_ID']}", raw, id_token)
        task = _format_task_dict(task, current_date)
    pending.sort(key=lambda t: (-t["Priority_Score"], t["Task_Deadline"]))
    return pending


def update_task(
    uid: str,
    id_token: str,
    task_id: str,
    title: str,
    subject: str,
    deadline: str,
    difficulty: int,
    importance: int,
    estimated_hours: Optional[float] = None,
    status: Optional[str] = None,
) -> bool:
    existing = _get_doc(uid, f"tasks/{task_id}", id_token)
    if not existing or existing.get("ownerUid") != uid:
        return False

    title = (title or "").strip()
    subject = (subject or "").strip()
    deadline_str = (deadline or "").strip()
    if not title or not subject or not deadline_str:
        raise ValueError("Please complete all required fields")

    formatted_deadline = parse_date(deadline_str).strftime("%Y-%m-%d")
    diff_val = int(difficulty)
    imp_val = int(importance)
    if not (1 <= diff_val <= 5) or not (1 <= imp_val <= 5):
        raise ValueError("Invalid input")

    hours_val = None
    if estimated_hours is not None and estimated_hours != "":
        val = float(estimated_hours)
        if val <= 0:
            raise ValueError("Invalid input")
        hours_val = val

    new_status = status if status in ("Pending", "Completed") else existing.get("Task_Status", "Pending")
    priority_score = calculate_priority(formatted_deadline, diff_val, imp_val, hours_val)

    existing.update({
        "ownerUid": uid,
        "Task_Title": title,
        "Task_Subject": subject,
        "Task_Deadline": formatted_deadline,
        "Task_Difficulty": diff_val,
        "Task_Importance": imp_val,
        "Estimated_Hours": hours_val,
        "Target_Hours": hours_val,
        "Priority_Score": priority_score,
        "Task_Status": new_status,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    })
    _set_doc(uid, f"tasks/{task_id}", existing, id_token)
    return True


def delete_task(uid: str, id_token: str, task_id: str) -> bool:
    existing = _get_doc(uid, f"tasks/{task_id}", id_token)
    if not existing or existing.get("ownerUid") != uid:
        return False
    active = _get_doc(uid, "active_session/current", id_token)
    if active and str(active.get("Task_ID")) == str(task_id):
        _delete_doc(uid, "active_session/current", id_token)
    return _delete_doc(uid, f"tasks/{task_id}", id_token)


def complete_task(uid: str, id_token: str, task_id: str) -> bool:
    existing = _get_doc(uid, f"tasks/{task_id}", id_token)
    if not existing or existing.get("ownerUid") != uid:
        return False
    active = _get_doc(uid, "active_session/current", id_token)
    if active and str(active.get("Task_ID")) == str(task_id):
        stop_tracking_session(uid, id_token)
        existing = _get_doc(uid, f"tasks/{task_id}", id_token) or existing

    existing["Task_Status"] = "Completed"
    existing["Completed_At"] = datetime.now().isoformat()
    existing["updatedAt"] = datetime.now(timezone.utc).isoformat()
    _set_doc(uid, f"tasks/{task_id}", existing, id_token)
    return True


def clear_all_tasks(uid: str, id_token: str) -> None:
    _delete_doc(uid, "active_session/current", id_token)
    for t in _list_collection(uid, "tasks", id_token):
        _delete_doc(uid, f"tasks/{t['_doc_id']}", id_token)
    for s in _list_collection(uid, "study_sessions", id_token):
        _delete_doc(uid, f"study_sessions/{s['_doc_id']}", id_token)


# =============================================================================
# Subtasks
# =============================================================================

def add_subtask(uid: str, id_token: str, task_id: str, title: str) -> str:
    title = (title or "").strip()
    if not title:
        raise ValueError("Subtask title cannot be empty")
    existing = _get_doc(uid, f"tasks/{task_id}", id_token)
    if not existing or existing.get("ownerUid") != uid:
        raise ValueError("Task not found")
    sub_id = uuid.uuid4().hex[:10]
    subs = existing.get("subtasks") or []
    subs.append({"Subtask_ID": sub_id, "Subtask_Title": title, "Is_Completed": 0})
    existing["subtasks"] = subs
    existing["updatedAt"] = datetime.now(timezone.utc).isoformat()
    _set_doc(uid, f"tasks/{task_id}", existing, id_token)
    return sub_id


def toggle_subtask(uid: str, id_token: str, subtask_id: str) -> bool:
    for t in _list_collection(uid, "tasks", id_token):
        subs = t.get("subtasks") or []
        changed = False
        for s in subs:
            if str(s.get("Subtask_ID")) == str(subtask_id):
                s["Is_Completed"] = 0 if s.get("Is_Completed") else 1
                changed = True
                break
        if changed:
            t["subtasks"] = subs
            t["updatedAt"] = datetime.now(timezone.utc).isoformat()
            _set_doc(uid, f"tasks/{t['_doc_id']}", t, id_token)
            return True
    return False


def delete_subtask(uid: str, id_token: str, subtask_id: str) -> bool:
    for t in _list_collection(uid, "tasks", id_token):
        subs = t.get("subtasks") or []
        filtered = [s for s in subs if str(s.get("Subtask_ID")) != str(subtask_id)]
        if len(filtered) != len(subs):
            t["subtasks"] = filtered
            t["updatedAt"] = datetime.now(timezone.utc).isoformat()
            _set_doc(uid, f"tasks/{t['_doc_id']}", t, id_token)
            return True
    return False


# =============================================================================
# Personal Study Routines
# =============================================================================

DAYS_ORDER = {
    "Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4,
    "Friday": 5, "Saturday": 6, "Sunday": 7, "Daily": 0,
}


def get_routines(uid: str, id_token: str) -> List[Dict[str, Any]]:
    docs = _list_collection(uid, "routines", id_token)
    routines = []
    for d in docs:
        if d.get("ownerUid", uid) != uid:
            continue
        routines.append({
            "Routine_ID": str(d.get("Routine_ID") or d.get("_doc_id")),
            "title": d.get("title", ""),
            "subject": d.get("subject", "General"),
            "dayOfWeek": d.get("dayOfWeek", "Monday"),
            "startTime": d.get("startTime", "17:00"),
            "endTime": d.get("endTime", "18:00"),
            "focusGoal": d.get("focusGoal", ""),
            "isActive": bool(d.get("isActive", True)),
        })
    routines.sort(key=lambda r: (DAYS_ORDER.get(r["dayOfWeek"], 9), r["startTime"]))
    return routines


def add_routine(
    uid: str,
    id_token: str,
    title: str,
    subject: str,
    day_of_week: str,
    start_time: str,
    end_time: str,
    focus_goal: str = "",
) -> str:
    title = (title or "").strip()
    subject = (subject or "").strip() or "General"
    day_of_week = (day_of_week or "").strip()
    if not title or day_of_week not in DAYS_ORDER:
        raise ValueError("Please provide a valid routine title and day of week.")

    routine_id = f"rtn_{int(time.time() * 1000)}_{uuid.uuid4().hex[:5]}"
    now_iso = datetime.now(timezone.utc).isoformat()
    payload = {
        "ownerUid": uid,
        "Routine_ID": routine_id,
        "title": title,
        "subject": subject,
        "dayOfWeek": day_of_week,
        "startTime": (start_time or "17:00").strip(),
        "endTime": (end_time or "18:00").strip(),
        "focusGoal": (focus_goal or "").strip(),
        "isActive": True,
        "createdAt": now_iso,
    }
    _set_doc(uid, f"routines/{routine_id}", payload, id_token)
    return routine_id


def toggle_routine(uid: str, id_token: str, routine_id: str) -> bool:
    doc = _get_doc(uid, f"routines/{routine_id}", id_token)
    if not doc or doc.get("ownerUid") != uid:
        return False
    doc["isActive"] = not bool(doc.get("isActive", True))
    _set_doc(uid, f"routines/{routine_id}", doc, id_token)
    return True


def delete_routine(uid: str, id_token: str, routine_id: str) -> bool:
    doc = _get_doc(uid, f"routines/{routine_id}", id_token)
    if not doc or doc.get("ownerUid") != uid:
        return False
    return _delete_doc(uid, f"routines/{routine_id}", id_token)


# =============================================================================
# Real-Time Time Intelligence & Session Tracking
# =============================================================================

def get_active_session(uid: str, id_token: str) -> Optional[Dict[str, Any]]:
    data = _get_doc(uid, "active_session/current", id_token)
    if not data or data.get("ownerUid") != uid:
        return None

    is_paused = bool(data.get("Is_Paused", False))
    accum = int(data.get("Accumulated_Seconds", 0))
    start_ts = float(data.get("Start_Timestamp", time.time()))
    now_ts = time.time()
    elapsed = accum if is_paused else accum + max(0, round(now_ts - start_ts))

    return {
        "has_active": True,
        "Task_ID": str(data.get("Task_ID")),
        "task_id": str(data.get("Task_ID")),
        "Session_ID": str(data.get("Session_ID")),
        "task_title": data.get("Task_Title", "Study Session"),
        "task_subject": data.get("Task_Subject", "Focus"),
        "elapsed_seconds": elapsed,
        "accumulated_seconds": accum,
        "elapsed_formatted": format_duration(elapsed),
        "is_paused": is_paused,
        "status": "paused" if is_paused else "started",
    }


def start_tracking_session(uid: str, id_token: str, task_id: str, force: bool = False) -> Dict[str, Any]:
    task = get_task_by_id(uid, id_token, str(task_id))
    if not task:
        raise ValueError("Task not found")

    existing_active = _get_doc(uid, "active_session/current", id_token)
    if existing_active:
        existing_tid = str(existing_active.get("Task_ID"))
        if existing_tid == str(task_id):
            if existing_active.get("Is_Paused"):
                return resume_tracking_session(uid, id_token)
            res = get_active_session(uid, id_token)
            if res:
                res["status"] = "active"
            return res
        if not force:
            return {
                "conflict": True,
                "has_conflict": True,
                "running_task": {
                    "task_id": existing_tid,
                    "title": existing_active.get("Task_Title", "Another Task"),
                },
                "current_task_id": existing_tid,
                "current_task_title": existing_active.get("Task_Title", "Another Task"),
                "message": f"Session already active for '{existing_active.get('Task_Title', 'another task')}'. Switch to this task?",
            }
        # Preserve previous session in StudySessions/paused state and stop cleanly
        stop_tracking_session(uid, id_token)

    now_dt = datetime.now()
    now_iso = now_dt.isoformat()
    today_str = now_dt.strftime("%Y-%m-%d")
    now_ts = time.time()
    session_id = f"sess_{int(now_ts * 1000)}_{uuid.uuid4().hex[:5]}"

    _set_doc(
        uid,
        f"study_sessions/{session_id}",
        {
            "ownerUid": uid,
            "Session_ID": session_id,
            "Task_ID": str(task_id),
            "Task_Title": task["Task_Title"],
            "Task_Subject": task["Task_Subject"],
            "Start_Time": now_iso,
            "End_Time": None,
            "Duration_Seconds": 0,
            "Session_Date": today_str,
            "Minutes_Spent": 0,
            "Status": "active",
            "Completed_At": "",
            "Created_At": now_iso,
        },
        id_token,
    )

    _set_doc(
        uid,
        "active_session/current",
        {
            "ownerUid": uid,
            "Task_ID": str(task_id),
            "Session_ID": session_id,
            "Task_Title": task["Task_Title"],
            "Task_Subject": task["Task_Subject"],
            "Start_Timestamp": now_ts,
            "Accumulated_Seconds": 0,
            "Is_Paused": False,
            "Paused_At": None,
            "Updated_At": now_iso,
        },
        id_token,
    )

    if not task.get("First_Tracked_At"):
        raw_t = _get_doc(uid, f"tasks/{task_id}", id_token)
        if raw_t:
            raw_t["First_Tracked_At"] = now_iso
            _set_doc(uid, f"tasks/{task_id}", raw_t, id_token)

    res = get_active_session(uid, id_token)
    if res:
        res["status"] = "started"
    return res


def pause_tracking_session(uid: str, id_token: str) -> Optional[Dict[str, Any]]:
    row = _get_doc(uid, "active_session/current", id_token)
    if not row:
        return None
    if row.get("Is_Paused"):
        return get_active_session(uid, id_token)

    now_ts = time.time()
    active_interval = max(0, round(now_ts - float(row.get("Start_Timestamp", now_ts))))
    new_accum = int(row.get("Accumulated_Seconds", 0)) + active_interval
    session_id = row.get("Session_ID")

    row.update({
        "Accumulated_Seconds": new_accum,
        "Is_Paused": True,
        "Paused_At": now_ts,
        "Updated_At": datetime.now().isoformat(),
    })
    _set_doc(uid, "active_session/current", row, id_token)

    if session_id:
        sdoc = _get_doc(uid, f"study_sessions/{session_id}", id_token)
        if sdoc:
            sdoc.update({
                "Duration_Seconds": new_accum,
                "Minutes_Spent": max(0, round(new_accum / 60)),
                "Status": "paused",
            })
            _set_doc(uid, f"study_sessions/{session_id}", sdoc, id_token)

    res = get_active_session(uid, id_token)
    if res:
        res["status"] = "paused"
    return res


def resume_tracking_session(uid: str, id_token: str) -> Optional[Dict[str, Any]]:
    row = _get_doc(uid, "active_session/current", id_token)
    if not row:
        return None
    if not row.get("Is_Paused"):
        return get_active_session(uid, id_token)

    now_ts = time.time()
    row.update({
        "Start_Timestamp": now_ts,
        "Is_Paused": False,
        "Paused_At": None,
        "Updated_At": datetime.now().isoformat(),
    })
    _set_doc(uid, "active_session/current", row, id_token)

    session_id = row.get("Session_ID")
    if session_id:
        sdoc = _get_doc(uid, f"study_sessions/{session_id}", id_token)
        if sdoc:
            sdoc["Status"] = "active"
            _set_doc(uid, f"study_sessions/{session_id}", sdoc, id_token)

    res = get_active_session(uid, id_token)
    if res:
        res["status"] = "resumed"
    return res


def stop_tracking_session(uid: str, id_token: str) -> Dict[str, Any]:
    row = _get_doc(uid, "active_session/current", id_token)
    if not row:
        return {"status": "stopped", "stopped": False, "message": "No active session"}

    now_ts = time.time()
    now_iso = datetime.now().isoformat()
    accum = int(row.get("Accumulated_Seconds", 0))
    if not row.get("Is_Paused"):
        total_sec = accum + max(0, round(now_ts - float(row.get("Start_Timestamp", now_ts))))
    else:
        total_sec = accum

    task_id = str(row.get("Task_ID"))
    session_id = str(row.get("Session_ID"))
    mins = max(1, round(total_sec / 60)) if total_sec > 0 else 0

    sdoc = _get_doc(uid, f"study_sessions/{session_id}", id_token)
    if sdoc:
        sdoc.update({
            "End_Time": now_iso,
            "Duration_Seconds": total_sec,
            "Minutes_Spent": mins,
            "Status": "completed",
            "Completed_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        _set_doc(uid, f"study_sessions/{session_id}", sdoc, id_token)

    tdoc = _get_doc(uid, f"tasks/{task_id}", id_token)
    if tdoc:
        tdoc["Total_Tracked_Seconds"] = int(tdoc.get("Total_Tracked_Seconds") or 0) + total_sec
        _set_doc(uid, f"tasks/{task_id}", tdoc, id_token)

    _delete_doc(uid, "active_session/current", id_token)

    return {
        "status": "stopped",
        "stopped": True,
        "task_id": task_id,
        "session_id": session_id,
        "duration_seconds": total_sec,
        "duration_formatted": format_duration(total_sec),
    }


def log_study_session(uid: str, id_token: str, task_id: Optional[str], minutes: int) -> str:
    today_str = date.today().strftime("%Y-%m-%d")
    now_dt = datetime.now()
    now_iso = now_dt.isoformat()
    duration_sec = int(minutes) * 60
    start_iso = (now_dt - timedelta(seconds=duration_sec)).isoformat()
    session_id = f"sess_{int(time.time() * 1000)}_{uuid.uuid4().hex[:5]}"

    task_title = "Deep Focus Session"
    task_subject = "General"
    if task_id:
        t = _get_doc(uid, f"tasks/{task_id}", id_token)
        if t and t.get("ownerUid") == uid:
            task_title = t.get("Task_Title", task_title)
            task_subject = t.get("Task_Subject", task_subject)
            t["Total_Tracked_Seconds"] = int(t.get("Total_Tracked_Seconds") or 0) + duration_sec
            if not t.get("First_Tracked_At"):
                t["First_Tracked_At"] = start_iso
            _set_doc(uid, f"tasks/{task_id}", t, id_token)

    _set_doc(
        uid,
        f"study_sessions/{session_id}",
        {
            "ownerUid": uid,
            "Session_ID": session_id,
            "Task_ID": str(task_id) if task_id else None,
            "Task_Title": task_title,
            "Task_Subject": task_subject,
            "Start_Time": start_iso,
            "End_Time": now_iso,
            "Duration_Seconds": duration_sec,
            "Session_Date": today_str,
            "Minutes_Spent": int(minutes),
            "Status": "completed",
            "Completed_At": now_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "Created_At": now_iso,
        },
        id_token,
    )
    return session_id


def get_task_sessions(uid: str, id_token: str, task_id: str) -> List[Dict[str, Any]]:
    docs = _list_collection(uid, "study_sessions", id_token)
    sessions = []
    for d in docs:
        if str(d.get("Task_ID")) == str(task_id) and int(d.get("Duration_Seconds") or 0) > 0:
            dur = int(d["Duration_Seconds"])
            sessions.append({
                "session_id": d.get("Session_ID") or d.get("_doc_id"),
                "task_id": str(task_id),
                "date": d.get("Session_Date", ""),
                "duration_seconds": dur,
                "duration_formatted": format_duration(dur),
                "status": d.get("Status", "completed"),
                "start_time": d.get("Start_Time", ""),
                "end_time": d.get("End_Time", ""),
            })
    sessions.sort(key=lambda s: s["start_time"], reverse=True)
    return sessions


def get_study_streak(uid: str, id_token: str, current_date: date = None) -> int:
    if current_date is None:
        current_date = date.today()
    sessions = _list_collection(uid, "study_sessions", id_token)
    tasks = _list_collection(uid, "tasks", id_token)
    active_dates = {
        s.get("Session_Date")
        for s in sessions
        if (int(s.get("Duration_Seconds") or 0) > 0 or int(s.get("Minutes_Spent") or 0) > 0) and s.get("Session_Date")
    }
    for t in tasks:
        if t.get("Task_Status") == "Completed" and t.get("Completed_At"):
            active_dates.add(str(t["Completed_At"])[:10])

    streak = 0
    check_date = current_date
    while True:
        d_str = check_date.strftime("%Y-%m-%d")
        if d_str in active_dates:
            streak += 1
            check_date -= timedelta(days=1)
        elif streak == 0 and check_date == current_date:
            check_date -= timedelta(days=1)
            if check_date.strftime("%Y-%m-%d") in active_dates:
                streak += 1
                check_date -= timedelta(days=1)
            else:
                break
        else:
            break
    return streak


def get_weekly_workload_heatmap(uid: str, id_token: str, current_date: date = None) -> List[Dict[str, Any]]:
    if current_date is None:
        current_date = date.today()
    pending = get_pending_tasks(uid, id_token, current_date)
    days_data = []
    for i in range(7):
        target_day = current_date + timedelta(days=i)
        day_str = target_day.strftime("%Y-%m-%d")
        day_tasks = [t for t in pending if t["Task_Deadline"] == day_str]
        task_count = len(day_tasks)
        total_hours = round(sum(float(t.get("Estimated_Hours") or 0) for t in day_tasks), 1)
        if total_hours >= 5.0 or task_count >= 3:
            intensity = "heavy"
        elif total_hours >= 2.5 or task_count >= 2:
            intensity = "medium"
        elif total_hours > 0 or task_count > 0:
            intensity = "light"
        else:
            intensity = "empty"
        days_data.append({
            "date": day_str,
            "day_name": target_day.strftime("%a"),
            "day_num": target_day.strftime("%d %b"),
            "task_count": task_count,
            "total_hours": total_hours,
            "intensity": intensity,
            "is_today": (i == 0),
        })
    return days_data


def get_daily_capacity(uid: str, id_token: str, current_date: date = None, max_safe_hours: float = 6.0) -> Dict[str, Any]:
    if current_date is None:
        current_date = date.today()
    today_str = current_date.strftime("%Y-%m-%d")
    due_tasks = [t for t in get_pending_tasks(uid, id_token, current_date) if t["Task_Deadline"] <= today_str]
    total_hours = round(sum(float(t.get("Estimated_Hours") or 0) for t in due_tasks), 1)
    task_count = len(due_tasks)
    percent = min(round((total_hours / max_safe_hours) * 100), 100) if max_safe_hours > 0 else 0
    is_overloaded = total_hours > max_safe_hours
    return {
        "scheduled_hours": total_hours,
        "max_safe_hours": max_safe_hours,
        "task_count": task_count,
        "percent": percent,
        "is_overloaded": is_overloaded,
        "excess_hours": round(total_hours - max_safe_hours, 1) if is_overloaded else 0.0,
    }


def get_time_intelligence_data(uid: str, id_token: str, current_date: date = None) -> Dict[str, Any]:
    if current_date is None:
        current_date = date.today()
    today_str = current_date.strftime("%Y-%m-%d")
    week_start = (current_date - timedelta(days=current_date.weekday())).strftime("%Y-%m-%d")
    month_start = current_date.strftime("%Y-%m-01")

    all_sessions = _list_collection(uid, "study_sessions", id_token)
    all_tasks = get_all_tasks(uid, id_token, current_date)
    tasks_by_id = {str(t["Task_ID"]): t for t in all_tasks}

    valid_sessions = [s for s in all_sessions if int(s.get("Duration_Seconds") or 0) > 0]
    total_seconds = sum(int(s["Duration_Seconds"]) for s in valid_sessions)
    today_seconds = sum(int(s["Duration_Seconds"]) for s in valid_sessions if s.get("Session_Date") == today_str)
    week_seconds = sum(int(s["Duration_Seconds"]) for s in valid_sessions if (s.get("Session_Date") or "") >= week_start)
    month_seconds = sum(int(s["Duration_Seconds"]) for s in valid_sessions if (s.get("Session_Date") or "") >= month_start)

    active_session = get_active_session(uid, id_token)
    active_elapsed = int(active_session["elapsed_seconds"]) if (active_session and active_session.get("has_active")) else 0

    live_today = today_seconds + active_elapsed
    live_week = week_seconds + active_elapsed
    live_month = month_seconds + active_elapsed
    live_total = total_seconds + active_elapsed

    completed_tasks = [t for t in all_tasks if t["Task_Status"] == "Completed"]
    completed_tracked = [t for t in completed_tasks if t["total_tracked_seconds"] > 0]
    avg_task_seconds = (
        round(sum(t["total_tracked_seconds"] for t in completed_tracked) / len(completed_tracked))
        if completed_tracked else 0
    )

    subj_map: Dict[str, Dict[str, Any]] = {}
    for s in valid_sessions:
        tid = str(s.get("Task_ID") or "")
        subj = (tasks_by_id.get(tid, {}).get("Task_Subject") or s.get("Task_Subject") or "General / Unassigned")
        entry = subj_map.setdefault(subj, {"seconds": 0, "task_ids": set()})
        entry["seconds"] += int(s["Duration_Seconds"])
        if tid:
            entry["task_ids"].add(tid)

    if active_elapsed > 0 and active_session:
        asub = active_session.get("task_subject") or "General"
        entry = subj_map.setdefault(asub, {"seconds": 0, "task_ids": set()})
        entry["seconds"] += active_elapsed

    subject_breakdown = []
    for subj, info in subj_map.items():
        sec = info["seconds"]
        subject_breakdown.append({
            "subject": subj,
            "seconds": sec,
            "formatted": format_duration(sec),
            "percent": round((sec / live_total) * 100, 1) if live_total > 0 else 0.0,
            "task_count": len(info["task_ids"]),
        })
    subject_breakdown.sort(key=lambda x: x["seconds"], reverse=True)

    valid_sessions.sort(key=lambda s: s.get("Start_Time", ""), reverse=True)
    recent_sessions = []
    for s in valid_sessions[:15]:
        dur = int(s["Duration_Seconds"])
        st_fmt = ""
        et_fmt = ""
        if s.get("Start_Time"):
            try:
                st_fmt = datetime.fromisoformat(s["Start_Time"]).strftime("%H:%M")
            except Exception:
                st_fmt = str(s["Start_Time"])
        if s.get("End_Time"):
            try:
                et_fmt = datetime.fromisoformat(s["End_Time"]).strftime("%H:%M")
            except Exception:
                et_fmt = str(s["End_Time"])
        tid = str(s.get("Task_ID") or "")
        t_obj = tasks_by_id.get(tid, {})
        recent_sessions.append({
            "session_id": s.get("Session_ID") or s.get("_doc_id"),
            "task_id": tid or None,
            "task_title": t_obj.get("Task_Title") or s.get("Task_Title") or "Deep Focus Session",
            "task_subject": t_obj.get("Task_Subject") or s.get("Task_Subject") or "General",
            "date": s.get("Session_Date", ""),
            "time_range": f"{st_fmt}–{et_fmt}" if st_fmt and et_fmt else (st_fmt or s.get("Session_Date", "")),
            "duration_seconds": dur,
            "duration_formatted": format_duration(dur),
            "status": s.get("Status", "completed"),
        })

    completed_analytics = []
    for ct in completed_tracked[:10]:
        completed_analytics.append({
            "task_id": ct["Task_ID"],
            "task_title": ct["Task_Title"],
            "task_subject": ct["Task_Subject"],
            "focus_seconds": ct["total_tracked_seconds"],
            "focus_formatted": format_duration(ct["total_tracked_seconds"]),
            "calendar_span": ct.get("calendar_span_formatted") or "Same day",
        })

    streak_count = get_study_streak(uid, id_token, current_date)
    insights = []
    if live_today > 0:
        insights.append(f"You recorded {format_duration(live_today)} of focused study time today.")
    else:
        insights.append("No study sessions recorded yet today. Click 'Track Time' on any task to begin logging focused work.")
    if subject_breakdown:
        top = subject_breakdown[0]
        insights.append(f"{top['subject']} is your primary focus area, representing {top['percent']}% of recorded focus time ({top['formatted']}).")
    if completed_tracked:
        insights.append(f"Your average actual completion time across {len(completed_tracked)} completed task(s) is {format_duration(avg_task_seconds)}.")
    if streak_count >= 1:
        insights.append(f"🔥 Active Study Streak: You have maintained genuine study focus for {streak_count} consecutive day{'s' if streak_count != 1 else ''}!")

    return {
        "today_seconds": live_today,
        "today_completed_seconds": today_seconds,
        "today_formatted": format_duration(live_today),
        "week_seconds": live_week,
        "week_completed_seconds": week_seconds,
        "week_formatted": format_duration(live_week),
        "month_seconds": live_month,
        "month_completed_seconds": month_seconds,
        "month_formatted": format_duration(live_month),
        "total_seconds": live_total,
        "total_completed_seconds": total_seconds,
        "total_formatted": format_duration(live_total),
        "active_session": active_session,
        "active_elapsed_seconds": active_elapsed,
        "has_active_session": bool(active_session and active_session.get("has_active")),
        "total_sessions_count": len(valid_sessions) + (1 if active_elapsed > 0 else 0),
        "completed_tasks_count": len(completed_tasks),
        "avg_task_seconds": avg_task_seconds,
        "avg_task_formatted": format_duration(avg_task_seconds) if avg_task_seconds > 0 else "N/A",
        "streak_days": streak_count,
        "subject_breakdown": subject_breakdown,
        "recent_sessions": recent_sessions,
        "completed_analytics": completed_analytics,
        "insights": insights,
    }
