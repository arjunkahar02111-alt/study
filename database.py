"""
Database management module for Smart Study Planner.
Handles SQLite relational database creation, task queries, updates, and transactions.
"""

import sqlite3
import time
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from priority_calculator import (
    calculate_priority,
    calculate_urgency,
    calculate_workload,
    days_remaining,
    is_overdue,
    parse_date,
)

DEFAULT_DB_PATH = "study_planner.db"


def format_duration(seconds: Union[int, float, None]) -> str:
    """Formats seconds into human-readable duration string (e.g. '2h 15m' or '45m 20s')."""
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


def get_db_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Creates a connection to SQLite database with row factory for dictionary-like access."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initializes the database and creates/migrates Tasks, Subtasks, StudySessions, and ActiveSession tables."""
    conn = get_db_connection(db_path)
    with conn:
        cursor = conn.cursor()

        # Check if Tasks table exists
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='Tasks'")
        tasks_schema = cursor.fetchone()

        if not tasks_schema:
            conn.execute("""
                CREATE TABLE Tasks (
                    Task_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Task_Title TEXT NOT NULL,
                    Task_Subject TEXT NOT NULL,
                    Task_Deadline TEXT NOT NULL,
                    Task_Difficulty INTEGER NOT NULL CHECK (Task_Difficulty BETWEEN 1 AND 5),
                    Task_Importance INTEGER NOT NULL CHECK (Task_Importance BETWEEN 1 AND 5),
                    Estimated_Hours REAL DEFAULT NULL,
                    Target_Hours REAL DEFAULT NULL,
                    Total_Tracked_Seconds INTEGER NOT NULL DEFAULT 0,
                    Priority_Score REAL NOT NULL,
                    Task_Status TEXT NOT NULL DEFAULT 'Pending' CHECK (Task_Status IN ('Pending', 'Completed')),
                    First_Tracked_At TEXT DEFAULT NULL,
                    Completed_At TEXT DEFAULT NULL
                );
            """)
        else:
            schema_sql = tasks_schema["sql"]
            # If Tasks table has "Estimated_Hours REAL NOT NULL", migrate it safely to allow nullable/optional target
            if "Estimated_Hours REAL NOT NULL" in schema_sql:
                cursor.execute("PRAGMA foreign_keys = OFF")
                cursor.execute("""
                    CREATE TABLE Tasks_v31 (
                        Task_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                        Task_Title TEXT NOT NULL,
                        Task_Subject TEXT NOT NULL,
                        Task_Deadline TEXT NOT NULL,
                        Task_Difficulty INTEGER NOT NULL CHECK (Task_Difficulty BETWEEN 1 AND 5),
                        Task_Importance INTEGER NOT NULL CHECK (Task_Importance BETWEEN 1 AND 5),
                        Estimated_Hours REAL DEFAULT NULL,
                        Target_Hours REAL DEFAULT NULL,
                        Total_Tracked_Seconds INTEGER NOT NULL DEFAULT 0,
                        Priority_Score REAL NOT NULL,
                        Task_Status TEXT NOT NULL DEFAULT 'Pending' CHECK (Task_Status IN ('Pending', 'Completed')),
                        First_Tracked_At TEXT DEFAULT NULL,
                        Completed_At TEXT DEFAULT NULL
                    );
                """)
                cursor.execute("""
                    INSERT INTO Tasks_v31 (
                        Task_ID, Task_Title, Task_Subject, Task_Deadline, 
                        Task_Difficulty, Task_Importance, Estimated_Hours, 
                        Target_Hours, Total_Tracked_Seconds, Priority_Score, Task_Status
                    )
                    SELECT Task_ID, Task_Title, Task_Subject, Task_Deadline, 
                           Task_Difficulty, Task_Importance, Estimated_Hours, 
                           Estimated_Hours, 0, Priority_Score, Task_Status 
                    FROM Tasks;
                """)
                cursor.execute("DROP TABLE Tasks")
                cursor.execute("ALTER TABLE Tasks_v31 RENAME TO Tasks")
                cursor.execute("PRAGMA foreign_keys = ON")

            # Check and add any missing columns in Tasks
            cursor.execute("PRAGMA table_info(Tasks)")
            columns = {col["name"] for col in cursor.fetchall()}
            if "Total_Tracked_Seconds" not in columns:
                cursor.execute("ALTER TABLE Tasks ADD COLUMN Total_Tracked_Seconds INTEGER NOT NULL DEFAULT 0")
            if "Target_Hours" not in columns:
                cursor.execute("ALTER TABLE Tasks ADD COLUMN Target_Hours REAL DEFAULT NULL")
            if "First_Tracked_At" not in columns:
                cursor.execute("ALTER TABLE Tasks ADD COLUMN First_Tracked_At TEXT DEFAULT NULL")
            if "Completed_At" not in columns:
                cursor.execute("ALTER TABLE Tasks ADD COLUMN Completed_At TEXT DEFAULT NULL")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS Subtasks (
                Subtask_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                Task_ID INTEGER NOT NULL,
                Subtask_Title TEXT NOT NULL,
                Is_Completed INTEGER NOT NULL DEFAULT 0 CHECK (Is_Completed IN (0, 1)),
                FOREIGN KEY (Task_ID) REFERENCES Tasks(Task_ID) ON DELETE CASCADE
            );
        """)

        # StudySessions table with duration_seconds and start/end timestamps
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='StudySessions'")
        session_schema = cursor.fetchone()
        if not session_schema:
            conn.execute("""
                CREATE TABLE StudySessions (
                    Session_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Task_ID INTEGER,
                    Start_Time TEXT NOT NULL DEFAULT '',
                    End_Time TEXT,
                    Duration_Seconds INTEGER NOT NULL DEFAULT 0,
                    Session_Date TEXT NOT NULL,
                    Minutes_Spent INTEGER NOT NULL DEFAULT 0,
                    Status TEXT NOT NULL DEFAULT 'completed',
                    Completed_At TEXT NOT NULL DEFAULT '',
                    Created_At TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY (Task_ID) REFERENCES Tasks(Task_ID) ON DELETE SET NULL
                );
            """)
        else:
            cursor.execute("PRAGMA table_info(StudySessions)")
            s_cols = {col["name"] for col in cursor.fetchall()}
            if "Duration_Seconds" not in s_cols:
                cursor.execute("ALTER TABLE StudySessions ADD COLUMN Duration_Seconds INTEGER NOT NULL DEFAULT 0")
            if "Start_Time" not in s_cols:
                cursor.execute("ALTER TABLE StudySessions ADD COLUMN Start_Time TEXT NOT NULL DEFAULT ''")
            if "End_Time" not in s_cols:
                cursor.execute("ALTER TABLE StudySessions ADD COLUMN End_Time TEXT DEFAULT NULL")
            if "Status" not in s_cols:
                cursor.execute("ALTER TABLE StudySessions ADD COLUMN Status TEXT NOT NULL DEFAULT 'completed'")
            if "Created_At" not in s_cols:
                cursor.execute("ALTER TABLE StudySessions ADD COLUMN Created_At TEXT NOT NULL DEFAULT ''")

        # Single active session table (ID = 1 enforced)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ActiveSession (
                ID INTEGER PRIMARY KEY CHECK (ID = 1),
                Task_ID INTEGER NOT NULL,
                Session_ID INTEGER NOT NULL,
                Start_Timestamp REAL NOT NULL,
                Accumulated_Seconds INTEGER NOT NULL DEFAULT 0,
                Is_Paused INTEGER NOT NULL DEFAULT 0 CHECK (Is_Paused IN (0, 1)),
                Paused_At REAL DEFAULT NULL,
                Updated_At TEXT NOT NULL,
                FOREIGN KEY (Task_ID) REFERENCES Tasks(Task_ID) ON DELETE CASCADE,
                FOREIGN KEY (Session_ID) REFERENCES StudySessions(Session_ID) ON DELETE CASCADE
            );
        """)
    conn.close()


def add_task(
    title: str,
    subject: str,
    deadline: str,
    difficulty: int,
    importance: int,
    estimated_hours: Optional[float] = None,
    target_hours: Optional[float] = None,
    status: str = "Pending",
    db_path: str = DEFAULT_DB_PATH
) -> int:
    """
    Validates task input, calculates priority score, and inserts task into database.
    Does not require estimated hours. If target duration is supplied, records it as Target_Hours.
    Returns the new Task_ID.
    """
    title = title.strip() if title else ""
    subject = subject.strip() if subject else ""
    deadline_str = deadline.strip() if deadline else ""

    if not title or not subject or not deadline_str:
        raise ValueError("Please complete all required fields")

    # Validate deadline format
    try:
        parsed_deadline = parse_date(deadline_str)
        formatted_deadline = parsed_deadline.strftime("%Y-%m-%d")
    except Exception:
        raise ValueError("Invalid deadline format. Expected YYYY-MM-DD")

    try:
        diff_val = int(difficulty)
        imp_val = int(importance)
    except (ValueError, TypeError):
        raise ValueError("Invalid input")

    if not (1 <= diff_val <= 5) or not (1 <= imp_val <= 5):
        raise ValueError("Invalid input")

    # Optional target/estimated duration
    hours_val = None
    if estimated_hours is not None and estimated_hours != "":
        try:
            val = float(estimated_hours)
            if val <= 0:
                raise ValueError("Invalid input")
            hours_val = val
        except (ValueError, TypeError):
            raise ValueError("Invalid input")
    elif target_hours is not None and target_hours != "":
        try:
            val = float(target_hours)
            if val <= 0:
                raise ValueError("Invalid input")
            hours_val = val
        except (ValueError, TypeError):
            raise ValueError("Invalid input")

    priority_score = calculate_priority(
        formatted_deadline, diff_val, imp_val, hours_val
    )

    conn = get_db_connection(db_path)
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Tasks (
                Task_Title,
                Task_Subject,
                Task_Deadline,
                Task_Difficulty,
                Task_Importance,
                Estimated_Hours,
                Target_Hours,
                Total_Tracked_Seconds,
                Priority_Score,
                Task_Status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
        """, (
            title,
            subject,
            formatted_deadline,
            diff_val,
            imp_val,
            hours_val,
            hours_val,
            priority_score,
            status
        ))
        task_id = cursor.lastrowid
    conn.close()
    return task_id


def get_task_by_id(task_id: int, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    """Retrieves a single task by its Task_ID."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Tasks WHERE Task_ID = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return _format_task_dict(dict(row))
    return None


def get_all_tasks(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Fetches all tasks from the database."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Tasks ORDER BY Task_Deadline ASC, Priority_Score DESC")
    rows = cursor.fetchall()
    conn.close()
    return [_format_task_dict(dict(row)) for row in rows]


def get_pending_tasks(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Fetches all pending tasks."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Tasks WHERE Task_Status = 'Pending' ORDER BY Task_Deadline ASC")
    rows = cursor.fetchall()
    conn.close()
    return [_format_task_dict(dict(row)) for row in rows]


def get_completed_tasks(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Fetches all completed tasks."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Tasks WHERE Task_Status = 'Completed' ORDER BY Task_Deadline DESC")
    rows = cursor.fetchall()
    conn.close()
    return [_format_task_dict(dict(row)) for row in rows]


def get_overdue_tasks(db_path: str = DEFAULT_DB_PATH, current_date: date = None) -> List[Dict[str, Any]]:
    """Fetches all pending tasks whose deadline is earlier than current_date."""
    if current_date is None:
        current_date = date.today()
    current_date_str = current_date.strftime("%Y-%m-%d")

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM Tasks 
        WHERE Task_Status = 'Pending' AND Task_Deadline < ?
        ORDER BY Task_Deadline ASC
    """, (current_date_str,))
    rows = cursor.fetchall()
    conn.close()
    return [_format_task_dict(dict(row), current_date) for row in rows]


def get_upcoming_tasks(days_ahead: int = 7, db_path: str = DEFAULT_DB_PATH, current_date: date = None) -> List[Dict[str, Any]]:
    """
    Fetches pending tasks with deadlines between current_date and current_date + days_ahead.
    """
    if current_date is None:
        current_date = date.today()
    max_date = current_date + timedelta(days=days_ahead)
    
    current_date_str = current_date.strftime("%Y-%m-%d")
    max_date_str = max_date.strftime("%Y-%m-%d")

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM Tasks 
        WHERE Task_Status = 'Pending' 
          AND Task_Deadline >= ? 
          AND Task_Deadline <= ?
        ORDER BY Task_Deadline ASC, Priority_Score DESC
    """, (current_date_str, max_date_str))
    rows = cursor.fetchall()
    conn.close()
    return [_format_task_dict(dict(row), current_date) for row in rows]


def get_study_plan(db_path: str = DEFAULT_DB_PATH, current_date: date = None) -> List[Dict[str, Any]]:
    """
    Generates the organized study plan as defined in Criterion B Pseudocode:
    1. Fetch all pending tasks
    2. Recalculate priority score dynamically based on current date
    3. Identify overdue tasks (deadline < current_date)
    4. Sort pending tasks by Priority_Score in descending order
    """
    if current_date is None:
        current_date = date.today()

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Tasks WHERE Task_Status = 'Pending'")
    rows = cursor.fetchall()

    tasks = []
    # Recalculate and update priority scores if changed
    cursor_update = conn.cursor()
    for row in rows:
        task = dict(row)
        score = calculate_priority(
            task["Task_Deadline"],
            task["Task_Difficulty"],
            task["Task_Importance"],
            task["Estimated_Hours"],
            current_date=current_date
        )
        task["Priority_Score"] = score
        formatted = _format_task_dict(task, current_date)
        formatted["subtasks"] = get_subtasks_for_task(task["Task_ID"], db_path)
        tasks.append(formatted)
        
        # Keep database priority score updated dynamically
        cursor_update.execute(
            "UPDATE Tasks SET Priority_Score = ? WHERE Task_ID = ?",
            (score, task["Task_ID"])
        )
    conn.commit()
    conn.close()

    # Sort descending by priority score; tie-break by deadline ascending
    tasks.sort(key=lambda t: (-t["Priority_Score"], t["Task_Deadline"]))
    return tasks


def update_task(
    task_id: int,
    title: str,
    subject: str,
    deadline: str,
    difficulty: int,
    importance: int,
    estimated_hours: Optional[float] = None,
    target_hours: Optional[float] = None,
    status: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH
) -> bool:
    """
    Updates an existing task.
    Validates inputs and recalculates priority score.
    Target duration is optional.
    """
    existing = get_task_by_id(task_id, db_path)
    if not existing:
        return False

    title = title.strip() if title else ""
    subject = subject.strip() if subject else ""
    deadline_str = deadline.strip() if deadline else ""

    if not title or not subject or not deadline_str:
        raise ValueError("Please complete all required fields")

    try:
        parsed_deadline = parse_date(deadline_str)
        formatted_deadline = parsed_deadline.strftime("%Y-%m-%d")
    except Exception:
        raise ValueError("Invalid deadline format. Expected YYYY-MM-DD")

    try:
        diff_val = int(difficulty)
        imp_val = int(importance)
    except (ValueError, TypeError):
        raise ValueError("Invalid input")

    if not (1 <= diff_val <= 5) or not (1 <= imp_val <= 5):
        raise ValueError("Invalid input")

    hours_val = None
    if estimated_hours is not None and estimated_hours != "":
        try:
            val = float(estimated_hours)
            if val <= 0:
                raise ValueError("Invalid input")
            hours_val = val
        except (ValueError, TypeError):
            raise ValueError("Invalid input")
    elif target_hours is not None and target_hours != "":
        try:
            val = float(target_hours)
            if val <= 0:
                raise ValueError("Invalid input")
            hours_val = val
        except (ValueError, TypeError):
            raise ValueError("Invalid input")

    new_status = status if status in ("Pending", "Completed") else existing["Task_Status"]
    priority_score = calculate_priority(formatted_deadline, diff_val, imp_val, hours_val)

    conn = get_db_connection(db_path)
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Tasks SET
                Task_Title = ?,
                Task_Subject = ?,
                Task_Deadline = ?,
                Task_Difficulty = ?,
                Task_Importance = ?,
                Estimated_Hours = ?,
                Target_Hours = ?,
                Priority_Score = ?,
                Task_Status = ?
            WHERE Task_ID = ?
        """, (
            title,
            subject,
            formatted_deadline,
            diff_val,
            imp_val,
            hours_val,
            hours_val,
            priority_score,
            new_status,
            task_id
        ))
    conn.close()
    return True


def delete_task(task_id: int, db_path: str = DEFAULT_DB_PATH) -> bool:
    """Deletes a task by Task_ID, safely clearing any active session for it."""
    existing = get_task_by_id(task_id, db_path)
    if not existing:
        return False

    conn = get_db_connection(db_path)
    with conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ActiveSession WHERE Task_ID = ?", (task_id,))
        cursor.execute("DELETE FROM Tasks WHERE Task_ID = ?", (task_id,))
    conn.close()
    return True


def complete_task(task_id: int, db_path: str = DEFAULT_DB_PATH) -> bool:
    """Marks a task as 'Completed', finalizing any active session and recording Completed_At."""
    existing = get_task_by_id(task_id, db_path)
    if not existing:
        return False

    # Finalize active tracking session if it belongs to this task
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ActiveSession WHERE Task_ID = ?", (task_id,))
    active_row = cursor.fetchone()
    conn.close()
    if active_row:
        stop_tracking_session(db_path)

    now_iso = datetime.now().isoformat()
    conn = get_db_connection(db_path)
    with conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Tasks SET Task_Status = 'Completed', Completed_At = ? WHERE Task_ID = ?", (now_iso, task_id))
    conn.close()
    return True


def clear_all_tasks(db_path: str = DEFAULT_DB_PATH) -> None:
    """Removes all tasks and sessions from the database and resets the autoincrement ID counter to 1."""
    conn = get_db_connection(db_path)
    with conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ActiveSession")
        cursor.execute("DELETE FROM Subtasks")
        cursor.execute("DELETE FROM StudySessions")
        cursor.execute("DELETE FROM Tasks")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('Tasks', 'Subtasks', 'StudySessions', 'ActiveSession')")
    conn.close()


def add_subtask(task_id: int, title: str, db_path: str = DEFAULT_DB_PATH) -> int:
    """Adds a subtask to an existing assignment."""
    title = title.strip()
    if not title:
        raise ValueError("Subtask title cannot be empty")
    conn = get_db_connection(db_path)
    with conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Subtasks (Task_ID, Subtask_Title, Is_Completed) VALUES (?, ?, 0)",
            (task_id, title)
        )
        subtask_id = cursor.lastrowid
    conn.close()
    return subtask_id


def toggle_subtask(subtask_id: int, db_path: str = DEFAULT_DB_PATH) -> bool:
    """Toggles completion status of a subtask (0 <-> 1)."""
    conn = get_db_connection(db_path)
    with conn:
        cursor = conn.cursor()
        cursor.execute("SELECT Is_Completed FROM Subtasks WHERE Subtask_ID = ?", (subtask_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        new_val = 0 if row["Is_Completed"] == 1 else 1
        cursor.execute("UPDATE Subtasks SET Is_Completed = ? WHERE Subtask_ID = ?", (new_val, subtask_id))
    conn.close()
    return True


def delete_subtask(subtask_id: int, db_path: str = DEFAULT_DB_PATH) -> bool:
    """Deletes a subtask."""
    conn = get_db_connection(db_path)
    with conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Subtasks WHERE Subtask_ID = ?", (subtask_id,))
    conn.close()
    return True


def get_subtasks_for_task(task_id: int, db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Retrieves all subtasks belonging to a specific task."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Subtasks WHERE Task_ID = ? ORDER BY Subtask_ID ASC", (task_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def log_study_session(task_id: Optional[int], minutes: int, db_path: str = DEFAULT_DB_PATH) -> int:
    """Logs a completed Pomodoro study focus session."""
    today_str = date.today().strftime("%Y-%m-%d")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    now_iso = datetime.now().isoformat()
    duration_sec = int(minutes) * 60
    conn = get_db_connection(db_path)
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO StudySessions (
                Task_ID, Start_Time, End_Time, Duration_Seconds, 
                Session_Date, Minutes_Spent, Status, Completed_At, Created_At
            ) VALUES (?, ?, ?, ?, ?, ?, 'completed', ?, ?)
        """, (task_id, now_iso, now_iso, duration_sec, today_str, minutes, now_str, now_iso))
        session_id = cursor.lastrowid
        if task_id:
            cursor.execute("UPDATE Tasks SET Total_Tracked_Seconds = Total_Tracked_Seconds + ? WHERE Task_ID = ?", (duration_sec, task_id))
    conn.close()
    return session_id


def get_study_streak(db_path: str = DEFAULT_DB_PATH, current_date: date = None) -> int:
    """
    Calculates consecutive days with active study sessions or completed tasks.
    Returns streak count (days).
    """
    if current_date is None:
        current_date = date.today()

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT Session_Date FROM StudySessions 
        ORDER BY Session_Date DESC
    """)
    session_dates = {row["Session_Date"] for row in cursor.fetchall()}
    conn.close()

    streak = 0
    check_date = current_date
    while True:
        date_str = check_date.strftime("%Y-%m-%d")
        if date_str in session_dates:
            streak += 1
            check_date -= timedelta(days=1)
        elif streak == 0 and (check_date == current_date):
            # If user hasn't studied today yet, check yesterday to see if streak is alive
            check_date -= timedelta(days=1)
            date_str = check_date.strftime("%Y-%m-%d")
            if date_str in session_dates:
                streak += 1
                check_date -= timedelta(days=1)
            else:
                break
        else:
            break
    return streak


def get_weekly_workload_heatmap(db_path: str = DEFAULT_DB_PATH, current_date: date = None) -> List[Dict[str, Any]]:
    """
    Builds a 7-day workload density model (today + 6 days).
    Returns list of daily objects with date, day name, tasks count, total hours, and density tier.
    """
    if current_date is None:
        current_date = date.today()

    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    days_data = []
    for i in range(7):
        target_day = current_date + timedelta(days=i)
        day_str = target_day.strftime("%Y-%m-%d")
        
        cursor.execute("""
            SELECT COUNT(*) AS task_count, COALESCE(SUM(Estimated_Hours), 0) AS total_hours 
            FROM Tasks 
            WHERE Task_Status = 'Pending' AND Task_Deadline = ?
        """, (day_str,))
        row = cursor.fetchone()
        task_count = row["task_count"]
        total_hours = round(float(row["total_hours"]), 1)

        # Intensity tier
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
            "is_today": (i == 0)
        })

    conn.close()
    return days_data


def get_daily_capacity(db_path: str = DEFAULT_DB_PATH, current_date: date = None, max_safe_hours: float = 6.0) -> Dict[str, Any]:
    """
    Calculates workload capacity for tasks due today or overdue.
    Provides overload warning if total hours exceed max_safe_hours.
    """
    if current_date is None:
        current_date = date.today()
    today_str = current_date.strftime("%Y-%m-%d")

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) AS task_count, COALESCE(SUM(Estimated_Hours), 0) AS total_hours 
        FROM Tasks 
        WHERE Task_Status = 'Pending' AND Task_Deadline <= ?
    """, (today_str,))
    row = cursor.fetchone()
    conn.close()

    total_hours = round(float(row["total_hours"]), 1)
    task_count = row["task_count"]
    percent = min(round((total_hours / max_safe_hours) * 100), 100) if max_safe_hours > 0 else 0
    is_overloaded = total_hours > max_safe_hours

    return {
        "scheduled_hours": total_hours,
        "max_safe_hours": max_safe_hours,
        "task_count": task_count,
        "percent": percent,
        "is_overloaded": is_overloaded,
        "excess_hours": round(total_hours - max_safe_hours, 1) if is_overloaded else 0.0
    }




def _format_task_dict(task: Dict[str, Any], current_date: date = None) -> Dict[str, Any]:
    """Appends calculated UI helper fields to task dictionary."""
    if current_date is None:
        current_date = date.today()

    deadline_val = task["Task_Deadline"]
    overdue = is_overdue(deadline_val, current_date)
    days_left = days_remaining(deadline_val, current_date)
    urgency_val = calculate_urgency(deadline_val, current_date)
    workload_val = calculate_workload(task.get("Estimated_Hours") or task.get("Target_Hours"))

    task["is_overdue"] = overdue
    task["days_remaining"] = days_left
    task["urgency"] = urgency_val
    task["workload"] = workload_val

    # Real-time tracked time formatting
    tracked_sec = int(task.get("Total_Tracked_Seconds") or 0)
    task["total_tracked_seconds"] = tracked_sec
    task["tracked_time_formatted"] = format_duration(tracked_sec) if tracked_sec > 0 else "0m"

    # Completed analytics: actual focus vs calendar span
    if task.get("Completed_At") and task.get("First_Tracked_At"):
        try:
            start_dt = datetime.fromisoformat(task["First_Tracked_At"])
            comp_dt = datetime.fromisoformat(task["Completed_At"])
            cal_delta = comp_dt - start_dt
            cal_days = cal_delta.days
            cal_hours = cal_delta.seconds // 3600
            if cal_days > 0:
                task["calendar_span_formatted"] = f"{cal_days}d {cal_hours}h"
            else:
                task["calendar_span_formatted"] = f"{max(1, cal_hours)}h"
        except Exception:
            task["calendar_span_formatted"] = None
    else:
        task["calendar_span_formatted"] = None

    # Priority category tag
    score = task["Priority_Score"]
    if score >= 4.0:
        task["priority_category"] = "Urgent / High"
        task["badge_class"] = "badge-danger"
    elif score >= 3.0:
        task["priority_category"] = "Moderate"
        task["badge_class"] = "badge-warning"
    else:
        task["priority_category"] = "Low"
        task["badge_class"] = "badge-info"

    return task


# =============================================================================
# Real-Time Time Intelligence Engine
# =============================================================================

def get_active_session(db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    """Retrieves the single actively tracked study session if running or paused."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.ID, a.Task_ID, a.Session_ID, a.Start_Timestamp, a.Accumulated_Seconds, 
                   a.Is_Paused, a.Paused_At, a.Updated_At,
                   t.Task_Title, t.Task_Subject, t.Priority_Score
            FROM ActiveSession a
            JOIN Tasks t ON a.Task_ID = t.Task_ID
            WHERE a.ID = 1
        """)
        row = cursor.fetchone()
        if not row:
            return None

        data = dict(row)
        is_paused = bool(data["Is_Paused"])
        accum = int(data["Accumulated_Seconds"])
        start_ts = float(data["Start_Timestamp"])
        now_ts = time.time()

        if is_paused:
            elapsed = accum
        else:
            active_interval = max(0, round(now_ts - start_ts))
            elapsed = accum + active_interval

        data["has_active"] = True
        data["task_id"] = data["Task_ID"]
        data["task_title"] = data["Task_Title"]
        data["task_subject"] = data["Task_Subject"]
        data["elapsed_seconds"] = elapsed
        data["accumulated_seconds"] = accum
        data["elapsed_formatted"] = format_duration(elapsed)
        data["is_paused"] = is_paused
        data["status"] = "paused" if is_paused else "started"
        return data
    finally:
        conn.close()


def start_tracking_session(task_id: int, force: bool = False, db_path: str = DEFAULT_DB_PATH, force_switch: bool = False) -> Dict[str, Any]:
    """
    Starts an authoritative real-time focus session for a task.
    Enforces that only one task can be actively tracked at any time.
    """
    if isinstance(force, str):
        db_path = force
        force = False
    force = bool(force or force_switch)

    task = get_task_by_id(task_id, db_path)
    if not task:
        raise ValueError("Task not found")

    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ActiveSession WHERE ID = 1")
        existing_active = cursor.fetchone()
        if existing_active:
            existing_task_id = existing_active["Task_ID"]
            if existing_task_id == task_id:
                # Already active for this task; if paused, resume
                if existing_active["Is_Paused"]:
                    now_ts = time.time()
                    with conn:
                        cursor.execute("""
                            UPDATE ActiveSession 
                            SET Is_Paused = 0, Start_Timestamp = ?, Paused_At = NULL, Updated_At = ?
                            WHERE ID = 1
                        """, (now_ts, datetime.now().isoformat()))
                        cursor.execute("UPDATE StudySessions SET Status = 'active' WHERE Session_ID = ?", (existing_active["Session_ID"],))
                res = get_active_session(db_path)
                if res:
                    res["status"] = "resumed" if existing_active["Is_Paused"] else "active"
                return res
            elif not force:
                # Conflict: active session belongs to a different task
                cursor.execute("SELECT Task_Title, Task_Subject FROM Tasks WHERE Task_ID = ?", (existing_task_id,))
                active_t = cursor.fetchone()
                return {
                    "conflict": True,
                    "has_conflict": True,
                    "running_task": {
                        "task_id": existing_task_id,
                        "title": active_t["Task_Title"] if active_t else "Another Task"
                    },
                    "current_task_id": existing_task_id,
                    "current_task_title": active_t["Task_Title"] if active_t else "Another Task",
                    "message": f"Session already active for '{active_t['Task_Title'] if active_t else 'another task'}'. Pause or stop it first?"
                }
            else:
                # Force switch: stop previous task session cleanly
                stop_tracking_session(db_path)
                return start_tracking_session(task_id, force=False, db_path=db_path)

        now_dt = datetime.now()
        today_str = now_dt.strftime("%Y-%m-%d")
        now_iso = now_dt.isoformat()
        now_ts = time.time()

        with conn:
            cursor.execute("""
                INSERT INTO StudySessions (
                    Task_ID, Start_Time, Session_Date, Duration_Seconds, 
                    Minutes_Spent, Status, Completed_At, Created_At
                ) VALUES (?, ?, ?, 0, 0, 'active', '', ?)
            """, (task_id, now_iso, today_str, now_iso))
            session_id = cursor.lastrowid

            cursor.execute("""
                INSERT OR REPLACE INTO ActiveSession (
                    ID, Task_ID, Session_ID, Start_Timestamp, 
                    Accumulated_Seconds, Is_Paused, Updated_At
                ) VALUES (1, ?, ?, ?, 0, 0, ?)
            """, (task_id, session_id, now_ts, now_iso))

            if not task.get("First_Tracked_At"):
                cursor.execute("UPDATE Tasks SET First_Tracked_At = ? WHERE Task_ID = ?", (now_iso, task_id))
    finally:
        conn.close()

    res = get_active_session(db_path)
    if res:
        res["status"] = "started"
    return res


def pause_tracking_session(db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    """Pauses the currently active session without losing accumulated seconds."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ActiveSession WHERE ID = 1")
        row = cursor.fetchone()
        if not row or row["Is_Paused"]:
            return get_active_session(db_path)

        now_ts = time.time()
        active_interval = max(0, round(now_ts - float(row["Start_Timestamp"])))
        new_accum = int(row["Accumulated_Seconds"]) + active_interval
        session_id = row["Session_ID"]

        with conn:
            cursor.execute("""
                UPDATE ActiveSession 
                SET Accumulated_Seconds = ?, Is_Paused = 1, Paused_At = ?, Updated_At = ?
                WHERE ID = 1
            """, (new_accum, now_ts, datetime.now().isoformat()))

            cursor.execute("""
                UPDATE StudySessions
                SET Duration_Seconds = ?, Minutes_Spent = ?, Status = 'paused'
                WHERE Session_ID = ?
            """, (new_accum, max(0, round(new_accum / 60)), session_id))
    finally:
        conn.close()

    res = get_active_session(db_path)
    if res:
        res["status"] = "paused"
    return res


def resume_tracking_session(db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    """Resumes a paused tracking session."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ActiveSession WHERE ID = 1")
        row = cursor.fetchone()
        if not row or not row["Is_Paused"]:
            return get_active_session(db_path)

        now_ts = time.time()
        with conn:
            cursor.execute("""
                UPDATE ActiveSession 
                SET Start_Timestamp = ?, Is_Paused = 0, Paused_At = NULL, Updated_At = ?
                WHERE ID = 1
            """, (now_ts, datetime.now().isoformat()))

            cursor.execute("""
                UPDATE StudySessions SET Status = 'active' WHERE Session_ID = ?
            """, (row["Session_ID"],))
    finally:
        conn.close()

    res = get_active_session(db_path)
    if res:
        res["status"] = "resumed"
    return res


def stop_tracking_session(db_path: str = DEFAULT_DB_PATH) -> Dict[str, Any]:
    """Stops the active session, persists exact duration to StudySessions and Tasks."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ActiveSession WHERE ID = 1")
        row = cursor.fetchone()
        if not row:
            return {"status": "stopped", "stopped": False, "message": "No active session"}

        now_ts = time.time()
        now_iso = datetime.now().isoformat()
        accum = int(row["Accumulated_Seconds"])
        is_paused = bool(row["Is_Paused"])

        if not is_paused:
            active_interval = max(0, round(now_ts - float(row["Start_Timestamp"])))
            total_sec = accum + active_interval
        else:
            total_sec = accum

        task_id = row["Task_ID"]
        session_id = row["Session_ID"]
        mins = max(1, round(total_sec / 60)) if total_sec > 0 else 0

        with conn:
            cursor.execute("""
                UPDATE StudySessions
                SET End_Time = ?, Duration_Seconds = ?, Minutes_Spent = ?, Status = 'completed', Completed_At = ?
                WHERE Session_ID = ?
            """, (now_iso, total_sec, mins, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), session_id))

            cursor.execute("""
                UPDATE Tasks
                SET Total_Tracked_Seconds = Total_Tracked_Seconds + ?
                WHERE Task_ID = ?
            """, (total_sec, task_id))

            cursor.execute("DELETE FROM ActiveSession WHERE ID = 1")
    finally:
        conn.close()

    return {
        "status": "stopped",
        "stopped": True,
        "task_id": task_id,
        "session_id": session_id,
        "duration_seconds": total_sec,
        "duration_formatted": format_duration(total_sec)
    }


def get_task_sessions(task_id: int, db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Retrieves all recorded focus sessions for a specific task."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT Session_ID, Task_ID, Start_Time, End_Time, Duration_Seconds, Session_Date, Status, Completed_At
        FROM StudySessions
        WHERE Task_ID = ? AND Duration_Seconds > 0
        ORDER BY Session_ID DESC
    """, (task_id,))
    rows = cursor.fetchall()
    conn.close()

    sessions = []
    for r in rows:
        dur = int(r["Duration_Seconds"])
        sessions.append({
            "session_id": r["Session_ID"],
            "task_id": r["Task_ID"],
            "date": r["Session_Date"],
            "duration_seconds": dur,
            "duration_formatted": format_duration(dur),
            "status": r["Status"],
            "start_time": r["Start_Time"],
            "end_time": r["End_Time"]
        })
    return sessions


def get_time_intelligence_data(db_path: str = DEFAULT_DB_PATH, current_date: date = None) -> Dict[str, Any]:
    """
    Computes comprehensive Time Intelligence metrics, subject breakdowns,
    session history timeline, and contextual smart insights derived entirely from real data.
    """
    if current_date is None:
        current_date = date.today()

    today_str = current_date.strftime("%Y-%m-%d")
    week_start = (current_date - timedelta(days=current_date.weekday())).strftime("%Y-%m-%d")
    month_start = current_date.strftime("%Y-%m-01")

    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Total recorded focus time
    cursor.execute("SELECT COALESCE(SUM(Duration_Seconds), 0) AS total_sec FROM StudySessions")
    total_seconds = int(cursor.fetchone()["total_sec"])

    # Today's focus time
    cursor.execute("SELECT COALESCE(SUM(Duration_Seconds), 0) AS today_sec FROM StudySessions WHERE Session_Date = ?", (today_str,))
    today_seconds = int(cursor.fetchone()["today_sec"])

    # This week's focus time
    cursor.execute("SELECT COALESCE(SUM(Duration_Seconds), 0) AS week_sec FROM StudySessions WHERE Session_Date >= ?", (week_start,))
    week_seconds = int(cursor.fetchone()["week_sec"])

    # This month's focus time
    cursor.execute("SELECT COALESCE(SUM(Duration_Seconds), 0) AS month_sec FROM StudySessions WHERE Session_Date >= ?", (month_start,))
    month_seconds = int(cursor.fetchone()["month_sec"])

    # Total focus sessions count
    cursor.execute("SELECT COUNT(*) AS count FROM StudySessions WHERE Duration_Seconds > 0")
    total_sessions_count = int(cursor.fetchone()["count"])

    # Completed tasks count
    cursor.execute("SELECT COUNT(*) AS count FROM Tasks WHERE Task_Status = 'Completed'")
    completed_tasks_count = int(cursor.fetchone()["count"])

    # Average actual time per completed task (that had tracked focus time)
    cursor.execute("""
        SELECT COUNT(*) AS c, COALESCE(SUM(Total_Tracked_Seconds), 0) AS total_sec 
        FROM Tasks 
        WHERE Task_Status = 'Completed' AND Total_Tracked_Seconds > 0
    """)
    row = cursor.fetchone()
    completed_tracked_count = row["c"]
    completed_tracked_sec = row["total_sec"]
    avg_task_seconds = round(completed_tracked_sec / completed_tracked_count) if completed_tracked_count > 0 else 0

    # Subject-wise time breakdown
    cursor.execute("""
        SELECT COALESCE(t.Task_Subject, 'General / Unassigned') AS subject, 
               COALESCE(SUM(s.Duration_Seconds), 0) AS subject_sec,
               COUNT(DISTINCT t.Task_ID) as task_count
        FROM StudySessions s
        LEFT JOIN Tasks t ON s.Task_ID = t.Task_ID
        WHERE s.Duration_Seconds > 0
        GROUP BY subject
        ORDER BY subject_sec DESC
    """)
    subject_rows = cursor.fetchall()
    subject_breakdown = []
    for sr in subject_rows:
        sec = int(sr["subject_sec"])
        pct = round((sec / total_seconds) * 100, 1) if total_seconds > 0 else 0
        subject_breakdown.append({
            "subject": sr["subject"],
            "seconds": sec,
            "formatted": format_duration(sec),
            "percent": pct,
            "task_count": sr["task_count"]
        })

    # Recent Session History Timeline
    cursor.execute("""
        SELECT s.Session_ID, s.Task_ID, s.Start_Time, s.End_Time, s.Duration_Seconds, 
               s.Session_Date, s.Status, s.Completed_At,
               COALESCE(t.Task_Title, 'Deep Focus Session') AS Task_Title,
               COALESCE(t.Task_Subject, 'General') AS Task_Subject
        FROM StudySessions s
        LEFT JOIN Tasks t ON s.Task_ID = t.Task_ID
        WHERE s.Duration_Seconds > 0
        ORDER BY s.Session_ID DESC
        LIMIT 15
    """)
    recent_sessions = []
    for r in cursor.fetchall():
        dur = int(r["Duration_Seconds"])
        start_fmt = ""
        end_fmt = ""
        if r["Start_Time"]:
            try:
                start_dt = datetime.fromisoformat(r["Start_Time"])
                start_fmt = start_dt.strftime("%H:%M")
            except Exception:
                start_fmt = r["Start_Time"]
        if r["End_Time"]:
            try:
                end_dt = datetime.fromisoformat(r["End_Time"])
                end_fmt = end_dt.strftime("%H:%M")
            except Exception:
                end_fmt = r["End_Time"]

        time_range = f"{start_fmt}–{end_fmt}" if start_fmt and end_fmt else (start_fmt or r["Session_Date"])
        recent_sessions.append({
            "session_id": r["Session_ID"],
            "task_id": r["Task_ID"],
            "task_title": r["Task_Title"],
            "task_subject": r["Task_Subject"],
            "date": r["Session_Date"],
            "time_range": time_range,
            "duration_seconds": dur,
            "duration_formatted": format_duration(dur),
            "status": r["Status"]
        })

    # Completed Task Analytics (Actual Focus vs Calendar Duration)
    cursor.execute("""
        SELECT Task_ID, Task_Title, Task_Subject, Total_Tracked_Seconds, First_Tracked_At, Completed_At
        FROM Tasks
        WHERE Task_Status = 'Completed' AND Total_Tracked_Seconds > 0
        ORDER BY Task_ID DESC
        LIMIT 10
    """)
    completed_analytics = []
    for ct in cursor.fetchall():
        focus_sec = int(ct["Total_Tracked_Seconds"])
        cal_str = "Same day"
        if ct["First_Tracked_At"] and ct["Completed_At"]:
            try:
                st = datetime.fromisoformat(ct["First_Tracked_At"])
                ed = datetime.fromisoformat(ct["Completed_At"])
                delta = ed - st
                days = delta.days
                hrs = delta.seconds // 3600
                if days > 0:
                    cal_str = f"{days}d {hrs}h"
                else:
                    cal_str = f"{max(1, hrs)}h"
            except Exception:
                cal_str = "Recorded"
        completed_analytics.append({
            "task_id": ct["Task_ID"],
            "task_title": ct["Task_Title"],
            "task_subject": ct["Task_Subject"],
            "focus_seconds": focus_sec,
            "focus_formatted": format_duration(focus_sec),
            "calendar_span": cal_str
        })

    # Genuine Study Streak (sessions >= 10 mins or completed tasks)
    cursor.execute("""
        SELECT DISTINCT Session_Date FROM StudySessions WHERE Duration_Seconds >= 600
        UNION
        SELECT DISTINCT substr(Completed_At, 1, 10) FROM Tasks WHERE Task_Status = 'Completed' AND Completed_At IS NOT NULL
        ORDER BY Session_Date DESC
    """)
    active_dates = {row[0] for row in cursor.fetchall() if row[0]}
    conn.close()

    streak_count = 0
    check_d = current_date
    while True:
        d_str = check_d.strftime("%Y-%m-%d")
        if d_str in active_dates:
            streak_count += 1
            check_d -= timedelta(days=1)
        elif streak_count == 0 and check_d == current_date:
            check_d -= timedelta(days=1)
            d_str = check_d.strftime("%Y-%m-%d")
            if d_str in active_dates:
                streak_count += 1
                check_d -= timedelta(days=1)
            else:
                break
        else:
            break

    # Contextual Smart Study Insights
    insights = []
    if today_seconds > 0:
        insights.append(f"You recorded {format_duration(today_seconds)} of focused study time today.")
    else:
        insights.append("No study sessions recorded yet today. Click 'Start Tracking' on any study task to begin logging focused work.")

    if subject_breakdown:
        top_subj = subject_breakdown[0]
        insights.append(f"{top_subj['subject']} is your primary focus area, representing {top_subj['percent']}% of recorded focus time ({top_subj['formatted']}).")

    if completed_tracked_count > 0:
        insights.append(f"Your average actual completion time across {completed_tracked_count} completed task(s) is {format_duration(avg_task_seconds)}.")

    if streak_count > 1:
        insights.append(f"🔥 Active Study Streak: You have maintained genuine study focus for {streak_count} consecutive days!")

    return {
        "today_seconds": today_seconds,
        "today_formatted": format_duration(today_seconds),
        "week_seconds": week_seconds,
        "week_formatted": format_duration(week_seconds),
        "month_seconds": month_seconds,
        "month_formatted": format_duration(month_seconds),
        "total_seconds": total_seconds,
        "total_formatted": format_duration(total_seconds),
        "total_sessions_count": total_sessions_count,
        "completed_tasks_count": completed_tasks_count,
        "avg_task_seconds": avg_task_seconds,
        "avg_task_formatted": format_duration(avg_task_seconds) if avg_task_seconds > 0 else "N/A",
        "streak_days": streak_count,
        "subject_breakdown": subject_breakdown,
        "recent_sessions": recent_sessions,
        "completed_analytics": completed_analytics,
        "insights": insights
    }


def seed_sample_tasks(db_path: str = DEFAULT_DB_PATH) -> None:
    """Seeds the database with representative student tasks for demonstration and testing."""
    today = date.today()
    sample_tasks = [
        {
            "title": "Mathematics Calculus Problem Set",
            "subject": "Mathematics",
            "deadline": (today + timedelta(days=1)).strftime("%Y-%m-%d"),
            "difficulty": 4,
            "importance": 5,
            "estimated_hours": 3.0,
            "status": "Pending"
        },
        {
            "title": "Physics Internal Assessment Draft",
            "subject": "Physics",
            "deadline": (today + timedelta(days=2)).strftime("%Y-%m-%d"),
            "difficulty": 5,
            "importance": 5,
            "estimated_hours": 6.5,
            "status": "Pending"
        },
        {
            "title": "Chemistry Chapter 4 Reading",
            "subject": "Chemistry",
            "deadline": (today - timedelta(days=1)).strftime("%Y-%m-%d"),  # Overdue
            "difficulty": 2,
            "importance": 4,
            "estimated_hours": 1.5,
            "status": "Pending"
        },
        {
            "title": "English Literature Essay on Hamlet",
            "subject": "English Literature",
            "deadline": (today + timedelta(days=5)).strftime("%Y-%m-%d"),
            "difficulty": 4,
            "importance": 4,
            "estimated_hours": 4.0,
            "status": "Pending"
        },
        {
            "title": "Spanish Vocabulary Flashcards",
            "subject": "Spanish",
            "deadline": (today + timedelta(days=12)).strftime("%Y-%m-%d"),
            "difficulty": 2,
            "importance": 2,
            "estimated_hours": 1.0,
            "status": "Pending"
        },
        {
            "title": "Computer Science Database Normalization",
            "subject": "Computer Science",
            "deadline": (today - timedelta(days=3)).strftime("%Y-%m-%d"),
            "difficulty": 3,
            "importance": 4,
            "estimated_hours": 2.5,
            "status": "Completed"
        }
    ]

    for item in sample_tasks:
        add_task(
            title=item["title"],
            subject=item["subject"],
            deadline=item["deadline"],
            difficulty=item["difficulty"],
            importance=item["importance"],
            estimated_hours=item["estimated_hours"],
            status=item["status"],
            db_path=db_path
        )
