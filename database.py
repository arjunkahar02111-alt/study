"""
Database management module for Smart Study Planner.
Handles SQLite relational database creation, task queries, updates, and transactions.
"""

import os
import shutil
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

if os.environ.get("VERCEL"):
    import tempfile
    DEFAULT_DB_PATH = os.path.join(tempfile.gettempdir(), "study_planner.db")
    orig_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "study_planner.db")
    if not os.path.exists(DEFAULT_DB_PATH) and os.path.exists(orig_db):
        try:
            shutil.copy2(orig_db, DEFAULT_DB_PATH)
        except Exception:
            pass
else:
    DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "study_planner.db")


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
    """Initializes the database and creates/migrates user-isolated Tasks, Subtasks, StudySessions, ActiveSession, Routines, UserProfiles, UserSettings, and MigrationLog tables."""
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
                    User_UID TEXT NOT NULL DEFAULT 'local_default',
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
            if "Estimated_Hours REAL NOT NULL" in schema_sql:
                cursor.execute("PRAGMA foreign_keys = OFF")
                cursor.execute("""
                    CREATE TABLE Tasks_v31 (
                        Task_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                        User_UID TEXT NOT NULL DEFAULT '__legacy__',
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
                        Task_ID, User_UID, Task_Title, Task_Subject, Task_Deadline, 
                        Task_Difficulty, Task_Importance, Estimated_Hours, 
                        Target_Hours, Total_Tracked_Seconds, Priority_Score, Task_Status
                    )
                    SELECT Task_ID, '__legacy__', Task_Title, Task_Subject, Task_Deadline, 
                           Task_Difficulty, Task_Importance, Estimated_Hours, 
                           Estimated_Hours, 0, Priority_Score, Task_Status 
                    FROM Tasks;
                """)
                cursor.execute("DROP TABLE Tasks")
                cursor.execute("ALTER TABLE Tasks_v31 RENAME TO Tasks")
                cursor.execute("PRAGMA foreign_keys = ON")

            cursor.execute("PRAGMA table_info(Tasks)")
            columns = {col["name"] for col in cursor.fetchall()}
            if "User_UID" not in columns:
                # Quarantine pre-auth rows under __legacy__ so no user inherits them automatically
                cursor.execute("ALTER TABLE Tasks ADD COLUMN User_UID TEXT NOT NULL DEFAULT '__legacy__'")
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

        # StudySessions table
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='StudySessions'")
        session_schema = cursor.fetchone()
        if not session_schema:
            conn.execute("""
                CREATE TABLE StudySessions (
                    Session_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                    User_UID TEXT NOT NULL DEFAULT 'local_default',
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
            if "User_UID" not in s_cols:
                cursor.execute("ALTER TABLE StudySessions ADD COLUMN User_UID TEXT NOT NULL DEFAULT '__legacy__'")
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

        # Per-user ActiveSession table (one active timer per User_UID)
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='ActiveSession'")
        active_schema = cursor.fetchone()
        if not active_schema:
            conn.execute("""
                CREATE TABLE ActiveSession (
                    User_UID TEXT PRIMARY KEY,
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
        else:
            cursor.execute("PRAGMA table_info(ActiveSession)")
            a_cols = {col["name"] for col in cursor.fetchall()}
            if "User_UID" not in a_cols:
                cursor.execute("PRAGMA foreign_keys = OFF")
                cursor.execute("""
                    CREATE TABLE ActiveSession_v4 (
                        User_UID TEXT PRIMARY KEY,
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
                cursor.execute("""
                    INSERT OR IGNORE INTO ActiveSession_v4 (
                        User_UID, Task_ID, Session_ID, Start_Timestamp, Accumulated_Seconds, Is_Paused, Paused_At, Updated_At
                    )
                    SELECT '__legacy__', Task_ID, Session_ID, Start_Timestamp, Accumulated_Seconds, Is_Paused, Paused_At, Updated_At
                    FROM ActiveSession;
                """)
                cursor.execute("DROP TABLE ActiveSession")
                cursor.execute("ALTER TABLE ActiveSession_v4 RENAME TO ActiveSession")
                cursor.execute("PRAGMA foreign_keys = ON")

        # Personal Weekly Study Routines table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS Routines (
                Routine_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                User_UID TEXT NOT NULL,
                Title TEXT NOT NULL,
                Subject TEXT NOT NULL,
                Day_Of_Week TEXT NOT NULL,
                Start_Time TEXT NOT NULL,
                End_Time TEXT NOT NULL,
                Focus_Goal TEXT DEFAULT '',
                Is_Active INTEGER NOT NULL DEFAULT 1 CHECK (Is_Active IN (0, 1)),
                Created_At TEXT NOT NULL
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS UserProfiles (
                User_UID TEXT PRIMARY KEY,
                Email TEXT NOT NULL DEFAULT '',
                Display_Name TEXT NOT NULL DEFAULT '',
                Photo_URL TEXT NOT NULL DEFAULT '',
                Created_At TEXT NOT NULL,
                Last_Login_At TEXT NOT NULL
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS UserSettings (
                User_UID TEXT PRIMARY KEY,
                Max_Safe_Hours REAL NOT NULL DEFAULT 6.0,
                Default_Focus_Minutes INTEGER NOT NULL DEFAULT 25,
                Sound_Effects_Enabled INTEGER NOT NULL DEFAULT 1,
                Updated_At TEXT NOT NULL
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS MigrationLog (
                Id INTEGER PRIMARY KEY CHECK (Id = 1),
                Migrated_To_UID TEXT DEFAULT NULL,
                Migrated_At TEXT DEFAULT NULL,
                Dismissed INTEGER NOT NULL DEFAULT 0
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
    db_path: str = DEFAULT_DB_PATH,
    user_uid: str = "local_default"
) -> int:
    """
    Validates task input, calculates priority score, and inserts task into database
    strictly scoped to user_uid.
    """
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

    priority_score = calculate_priority(
        formatted_deadline, diff_val, imp_val, hours_val
    )

    conn = get_db_connection(db_path)
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Tasks (
                User_UID,
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
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
        """, (
            user_uid,
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


def get_task_by_id(task_id: int, db_path: str = DEFAULT_DB_PATH, user_uid: str = "local_default") -> Optional[Dict[str, Any]]:
    """Retrieves a single task by Task_ID strictly owned by user_uid."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Tasks WHERE Task_ID = ? AND User_UID = ?", (task_id, user_uid))
    row = cursor.fetchone()
    conn.close()
    if row:
        return _format_task_dict(dict(row))
    return None


def get_all_tasks(db_path: str = DEFAULT_DB_PATH, user_uid: str = "local_default") -> List[Dict[str, Any]]:
    """Fetches all tasks owned by user_uid."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Tasks WHERE User_UID = ? ORDER BY Task_Deadline ASC, Priority_Score DESC", (user_uid,))
    rows = cursor.fetchall()
    conn.close()
    return [_format_task_dict(dict(row)) for row in rows]


def get_pending_tasks(db_path: str = DEFAULT_DB_PATH, user_uid: str = "local_default") -> List[Dict[str, Any]]:
    """Fetches all pending tasks owned by user_uid."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Tasks WHERE User_UID = ? AND Task_Status = 'Pending' ORDER BY Task_Deadline ASC", (user_uid,))
    rows = cursor.fetchall()
    conn.close()
    return [_format_task_dict(dict(row)) for row in rows]


def get_completed_tasks(db_path: str = DEFAULT_DB_PATH, user_uid: str = "local_default") -> List[Dict[str, Any]]:
    """Fetches all completed tasks owned by user_uid."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Tasks WHERE User_UID = ? AND Task_Status = 'Completed' ORDER BY Task_Deadline DESC", (user_uid,))
    rows = cursor.fetchall()
    conn.close()
    return [_format_task_dict(dict(row)) for row in rows]


def get_overdue_tasks(db_path: str = DEFAULT_DB_PATH, current_date: date = None, user_uid: str = "local_default") -> List[Dict[str, Any]]:
    """Fetches all pending tasks for user_uid whose deadline is earlier than current_date."""
    if current_date is None:
        current_date = date.today()
    current_date_str = current_date.strftime("%Y-%m-%d")

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM Tasks 
        WHERE User_UID = ? AND Task_Status = 'Pending' AND Task_Deadline < ?
        ORDER BY Task_Deadline ASC
    """, (user_uid, current_date_str))
    rows = cursor.fetchall()
    conn.close()
    return [_format_task_dict(dict(row), current_date) for row in rows]


def get_upcoming_tasks(days_ahead: int = 7, db_path: str = DEFAULT_DB_PATH, current_date: date = None, user_uid: str = "local_default") -> List[Dict[str, Any]]:
    """Fetches pending tasks for user_uid with deadlines within days_ahead."""
    if current_date is None:
        current_date = date.today()
    max_date = current_date + timedelta(days=days_ahead)

    current_date_str = current_date.strftime("%Y-%m-%d")
    max_date_str = max_date.strftime("%Y-%m-%d")

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM Tasks 
        WHERE User_UID = ?
          AND Task_Status = 'Pending' 
          AND Task_Deadline >= ? 
          AND Task_Deadline <= ?
        ORDER BY Task_Deadline ASC, Priority_Score DESC
    """, (user_uid, current_date_str, max_date_str))
    rows = cursor.fetchall()
    conn.close()
    return [_format_task_dict(dict(row), current_date) for row in rows]


def get_study_plan(db_path: str = DEFAULT_DB_PATH, current_date: date = None, user_uid: str = "local_default") -> List[Dict[str, Any]]:
    """Generates the organized study plan strictly for user_uid."""
    if current_date is None:
        current_date = date.today()

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Tasks WHERE User_UID = ? AND Task_Status = 'Pending'", (user_uid,))
    rows = cursor.fetchall()

    tasks = []
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

        cursor_update.execute(
            "UPDATE Tasks SET Priority_Score = ? WHERE Task_ID = ? AND User_UID = ?",
            (score, task["Task_ID"], user_uid)
        )
    conn.commit()
    conn.close()

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
    db_path: str = DEFAULT_DB_PATH,
    user_uid: str = "local_default"
) -> bool:
    """Updates an existing task owned by user_uid."""
    existing = get_task_by_id(task_id, db_path, user_uid=user_uid)
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
            WHERE Task_ID = ? AND User_UID = ?
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
            task_id,
            user_uid
        ))
    conn.close()
    return True


def delete_task(task_id: int, db_path: str = DEFAULT_DB_PATH, user_uid: str = "local_default") -> bool:
    """Deletes a task owned by user_uid, safely clearing any active session for it."""
    existing = get_task_by_id(task_id, db_path, user_uid=user_uid)
    if not existing:
        return False

    conn = get_db_connection(db_path)
    with conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ActiveSession WHERE Task_ID = ? AND User_UID = ?", (task_id, user_uid))
        cursor.execute("DELETE FROM Tasks WHERE Task_ID = ? AND User_UID = ?", (task_id, user_uid))
    conn.close()
    return True


def complete_task(task_id: int, db_path: str = DEFAULT_DB_PATH, user_uid: str = "local_default") -> bool:
    """Marks a task owned by user_uid as 'Completed', finalizing any active session."""
    existing = get_task_by_id(task_id, db_path, user_uid=user_uid)
    if not existing:
        return False

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ActiveSession WHERE Task_ID = ? AND User_UID = ?", (task_id, user_uid))
    active_row = cursor.fetchone()
    conn.close()
    if active_row:
        stop_tracking_session(db_path, user_uid=user_uid)

    now_iso = datetime.now().isoformat()
    conn = get_db_connection(db_path)
    with conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Tasks SET Task_Status = 'Completed', Completed_At = ? WHERE Task_ID = ? AND User_UID = ?", (now_iso, task_id, user_uid))
    conn.close()
    return True


def clear_all_tasks(db_path: str = DEFAULT_DB_PATH, user_uid: str = "local_default") -> None:
    """Removes all tasks and sessions belonging strictly to user_uid."""
    conn = get_db_connection(db_path)
    with conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ActiveSession WHERE User_UID = ?", (user_uid,))
        cursor.execute("DELETE FROM Subtasks WHERE Task_ID IN (SELECT Task_ID FROM Tasks WHERE User_UID = ?)", (user_uid,))
        cursor.execute("DELETE FROM StudySessions WHERE User_UID = ?", (user_uid,))
        cursor.execute("DELETE FROM Tasks WHERE User_UID = ?", (user_uid,))
    conn.close()


def add_subtask(task_id: int, title: str, db_path: str = DEFAULT_DB_PATH, user_uid: str = "local_default") -> int:
    """Adds a subtask to an assignment owned by user_uid."""
    title = title.strip()
    if not title:
        raise ValueError("Subtask title cannot be empty")
    if not get_task_by_id(task_id, db_path, user_uid=user_uid):
        raise ValueError("Task not found")
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


def toggle_subtask(subtask_id: int, db_path: str = DEFAULT_DB_PATH, user_uid: str = "local_default") -> bool:
    """Toggles completion status of a subtask owned by user_uid."""
    conn = get_db_connection(db_path)
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.Is_Completed FROM Subtasks s
            JOIN Tasks t ON s.Task_ID = t.Task_ID
            WHERE s.Subtask_ID = ? AND t.User_UID = ?
        """, (subtask_id, user_uid))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        new_val = 0 if row["Is_Completed"] == 1 else 1
        cursor.execute("UPDATE Subtasks SET Is_Completed = ? WHERE Subtask_ID = ?", (new_val, subtask_id))
    conn.close()
    return True


def delete_subtask(subtask_id: int, db_path: str = DEFAULT_DB_PATH, user_uid: str = "local_default") -> bool:
    """Deletes a subtask owned by user_uid."""
    conn = get_db_connection(db_path)
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM Subtasks
            WHERE Subtask_ID = ? AND Task_ID IN (SELECT Task_ID FROM Tasks WHERE User_UID = ?)
        """, (subtask_id, user_uid))
        deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def get_subtasks_for_task(task_id: int, db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Retrieves all subtasks belonging to a specific task."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Subtasks WHERE Task_ID = ? ORDER BY Subtask_ID ASC", (task_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def log_study_session(task_id: Optional[int], minutes: int, db_path: str = DEFAULT_DB_PATH, user_uid: str = "local_default") -> int:
    """Logs a completed Pomodoro study focus session strictly under user_uid."""
    today_str = date.today().strftime("%Y-%m-%d")
    now_dt = datetime.now()
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    now_iso = now_dt.isoformat()
    duration_sec = int(minutes) * 60
    start_dt = now_dt - timedelta(seconds=duration_sec)
    start_iso = start_dt.isoformat()
    conn = get_db_connection(db_path)
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO StudySessions (
                User_UID, Task_ID, Start_Time, End_Time, Duration_Seconds, 
                Session_Date, Minutes_Spent, Status, Completed_At, Created_At
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'completed', ?, ?)
        """, (user_uid, task_id, start_iso, now_iso, duration_sec, today_str, minutes, now_str, now_iso))
        session_id = cursor.lastrowid
        if task_id:
            cursor.execute("UPDATE Tasks SET Total_Tracked_Seconds = Total_Tracked_Seconds + ? WHERE Task_ID = ? AND User_UID = ?", (duration_sec, task_id, user_uid))
    conn.close()
    return session_id


def get_study_streak(db_path: str = DEFAULT_DB_PATH, current_date: date = None, user_uid: str = "local_default") -> int:
    """Calculates consecutive days with active study sessions or completed tasks for user_uid."""
    if current_date is None:
        current_date = date.today()

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT Session_Date FROM StudySessions WHERE User_UID = ? AND (Duration_Seconds > 0 OR Minutes_Spent > 0)
        UNION
        SELECT DISTINCT substr(Completed_At, 1, 10) FROM Tasks WHERE User_UID = ? AND Task_Status = 'Completed' AND Completed_At IS NOT NULL
        ORDER BY Session_Date DESC
    """, (user_uid, user_uid))
    session_dates = {row[0] for row in cursor.fetchall() if row[0]}
    conn.close()

    streak = 0
    check_date = current_date
    while True:
        date_str = check_date.strftime("%Y-%m-%d")
        if date_str in session_dates:
            streak += 1
            check_date -= timedelta(days=1)
        elif streak == 0 and (check_date == current_date):
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


def get_weekly_workload_heatmap(db_path: str = DEFAULT_DB_PATH, current_date: date = None, user_uid: str = "local_default") -> List[Dict[str, Any]]:
    """Builds a 7-day workload density model strictly for user_uid."""
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
            WHERE User_UID = ? AND Task_Status = 'Pending' AND Task_Deadline = ?
        """, (user_uid, day_str))
        row = cursor.fetchone()
        task_count = row["task_count"]
        total_hours = round(float(row["total_hours"]), 1)

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


def get_daily_capacity(db_path: str = DEFAULT_DB_PATH, current_date: date = None, max_safe_hours: float = 6.0, user_uid: str = "local_default") -> Dict[str, Any]:
    """Calculates workload capacity for user_uid."""
    if current_date is None:
        current_date = date.today()
    today_str = current_date.strftime("%Y-%m-%d")

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) AS task_count, COALESCE(SUM(Estimated_Hours), 0) AS total_hours 
        FROM Tasks 
        WHERE User_UID = ? AND Task_Status = 'Pending' AND Task_Deadline <= ?
    """, (user_uid, today_str))
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

def get_active_session(db_path: str = DEFAULT_DB_PATH, user_uid: str = "local_default") -> Optional[Dict[str, Any]]:
    """Retrieves the single actively tracked study session for user_uid."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.User_UID, a.Task_ID, a.Session_ID, a.Start_Timestamp, a.Accumulated_Seconds, 
                   a.Is_Paused, a.Paused_At, a.Updated_At,
                   t.Task_Title, t.Task_Subject, t.Priority_Score
            FROM ActiveSession a
            JOIN Tasks t ON a.Task_ID = t.Task_ID
            WHERE a.User_UID = ? AND t.User_UID = ?
        """, (user_uid, user_uid))
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


def start_tracking_session(task_id: int, force: bool = False, db_path: str = DEFAULT_DB_PATH, force_switch: bool = False, user_uid: str = "local_default") -> Dict[str, Any]:
    """Starts an authoritative real-time focus session for a task owned by user_uid."""
    if isinstance(force, str):
        db_path = force
        force = False
    force = bool(force or force_switch)

    task = get_task_by_id(task_id, db_path, user_uid=user_uid)
    if not task:
        raise ValueError("Task not found")

    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ActiveSession WHERE User_UID = ?", (user_uid,))
        existing_active = cursor.fetchone()
        if existing_active:
            existing_task_id = existing_active["Task_ID"]
            if existing_task_id == task_id:
                if existing_active["Is_Paused"]:
                    now_ts = time.time()
                    with conn:
                        cursor.execute("""
                            UPDATE ActiveSession 
                            SET Is_Paused = 0, Start_Timestamp = ?, Paused_At = NULL, Updated_At = ?
                            WHERE User_UID = ?
                        """, (now_ts, datetime.now().isoformat(), user_uid))
                        cursor.execute("UPDATE StudySessions SET Status = 'active' WHERE Session_ID = ? AND User_UID = ?", (existing_active["Session_ID"], user_uid))
                res = get_active_session(db_path, user_uid=user_uid)
                if res:
                    res["status"] = "resumed" if existing_active["Is_Paused"] else "active"
                return res
            elif not force:
                cursor.execute("SELECT Task_Title, Task_Subject FROM Tasks WHERE Task_ID = ? AND User_UID = ?", (existing_task_id, user_uid))
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
                stop_tracking_session(db_path, user_uid=user_uid)
                return start_tracking_session(task_id, force=False, db_path=db_path, user_uid=user_uid)

        now_dt = datetime.now()
        today_str = now_dt.strftime("%Y-%m-%d")
        now_iso = now_dt.isoformat()
        now_ts = time.time()

        with conn:
            cursor.execute("""
                INSERT INTO StudySessions (
                    User_UID, Task_ID, Start_Time, Session_Date, Duration_Seconds, 
                    Minutes_Spent, Status, Completed_At, Created_At
                ) VALUES (?, ?, ?, ?, 0, 0, 'active', '', ?)
            """, (user_uid, task_id, now_iso, today_str, now_iso))
            session_id = cursor.lastrowid

            cursor.execute("""
                INSERT OR REPLACE INTO ActiveSession (
                    User_UID, Task_ID, Session_ID, Start_Timestamp, 
                    Accumulated_Seconds, Is_Paused, Updated_At
                ) VALUES (?, ?, ?, ?, 0, 0, ?)
            """, (user_uid, task_id, session_id, now_ts, now_iso))

            if not task.get("First_Tracked_At"):
                cursor.execute("UPDATE Tasks SET First_Tracked_At = ? WHERE Task_ID = ? AND User_UID = ?", (now_iso, task_id, user_uid))
    finally:
        conn.close()

    res = get_active_session(db_path, user_uid=user_uid)
    if res:
        res["status"] = "started"
    return res


def pause_tracking_session(db_path: str = DEFAULT_DB_PATH, user_uid: str = "local_default") -> Optional[Dict[str, Any]]:
    """Pauses the active session for user_uid without losing accumulated seconds."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ActiveSession WHERE User_UID = ?", (user_uid,))
        row = cursor.fetchone()
        if not row or row["Is_Paused"]:
            return get_active_session(db_path, user_uid=user_uid)

        now_ts = time.time()
        active_interval = max(0, round(now_ts - float(row["Start_Timestamp"])))
        new_accum = int(row["Accumulated_Seconds"]) + active_interval
        session_id = row["Session_ID"]

        with conn:
            cursor.execute("""
                UPDATE ActiveSession 
                SET Accumulated_Seconds = ?, Is_Paused = 1, Paused_At = ?, Updated_At = ?
                WHERE User_UID = ?
            """, (new_accum, now_ts, datetime.now().isoformat(), user_uid))

            cursor.execute("""
                UPDATE StudySessions
                SET Duration_Seconds = ?, Minutes_Spent = ?, Status = 'paused'
                WHERE Session_ID = ? AND User_UID = ?
            """, (new_accum, max(0, round(new_accum / 60)), session_id, user_uid))
    finally:
        conn.close()

    res = get_active_session(db_path, user_uid=user_uid)
    if res:
        res["status"] = "paused"
    return res


def resume_tracking_session(db_path: str = DEFAULT_DB_PATH, user_uid: str = "local_default") -> Optional[Dict[str, Any]]:
    """Resumes a paused tracking session for user_uid."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ActiveSession WHERE User_UID = ?", (user_uid,))
        row = cursor.fetchone()
        if not row or not row["Is_Paused"]:
            return get_active_session(db_path, user_uid=user_uid)

        now_ts = time.time()
        with conn:
            cursor.execute("""
                UPDATE ActiveSession 
                SET Start_Timestamp = ?, Is_Paused = 0, Paused_At = NULL, Updated_At = ?
                WHERE User_UID = ?
            """, (now_ts, datetime.now().isoformat(), user_uid))

            cursor.execute("""
                UPDATE StudySessions SET Status = 'active' WHERE Session_ID = ? AND User_UID = ?
            """, (row["Session_ID"], user_uid))
    finally:
        conn.close()

    res = get_active_session(db_path, user_uid=user_uid)
    if res:
        res["status"] = "resumed"
    return res


def stop_tracking_session(db_path: str = DEFAULT_DB_PATH, user_uid: str = "local_default") -> Dict[str, Any]:
    """Stops the active session for user_uid and persists exact duration."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ActiveSession WHERE User_UID = ?", (user_uid,))
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
                WHERE Session_ID = ? AND User_UID = ?
            """, (now_iso, total_sec, mins, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), session_id, user_uid))

            cursor.execute("""
                UPDATE Tasks
                SET Total_Tracked_Seconds = Total_Tracked_Seconds + ?
                WHERE Task_ID = ? AND User_UID = ?
            """, (total_sec, task_id, user_uid))

            cursor.execute("DELETE FROM ActiveSession WHERE User_UID = ?", (user_uid,))
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


def get_task_sessions(task_id: int, db_path: str = DEFAULT_DB_PATH, user_uid: str = "local_default") -> List[Dict[str, Any]]:
    """Retrieves all recorded focus sessions for a specific task owned by user_uid."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT Session_ID, Task_ID, Start_Time, End_Time, Duration_Seconds, Session_Date, Status, Completed_At
        FROM StudySessions
        WHERE Task_ID = ? AND User_UID = ? AND Duration_Seconds > 0
        ORDER BY Session_ID DESC
    """, (task_id, user_uid))
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


def get_time_intelligence_data(db_path: str = DEFAULT_DB_PATH, current_date: date = None, user_uid: str = "local_default") -> Dict[str, Any]:
    """Computes Time Intelligence metrics strictly for user_uid."""
    if current_date is None:
        current_date = date.today()

    today_str = current_date.strftime("%Y-%m-%d")
    week_start = (current_date - timedelta(days=current_date.weekday())).strftime("%Y-%m-%d")
    month_start = current_date.strftime("%Y-%m-01")

    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT COALESCE(SUM(Duration_Seconds), 0) AS total_sec FROM StudySessions WHERE User_UID = ? AND Duration_Seconds > 0", (user_uid,))
    total_seconds = int(cursor.fetchone()["total_sec"])

    cursor.execute("SELECT COALESCE(SUM(Duration_Seconds), 0) AS today_sec FROM StudySessions WHERE User_UID = ? AND Session_Date = ? AND Duration_Seconds > 0", (user_uid, today_str))
    today_seconds = int(cursor.fetchone()["today_sec"])

    cursor.execute("SELECT COALESCE(SUM(Duration_Seconds), 0) AS week_sec FROM StudySessions WHERE User_UID = ? AND Session_Date >= ? AND Duration_Seconds > 0", (user_uid, week_start))
    week_seconds = int(cursor.fetchone()["week_sec"])

    cursor.execute("SELECT COALESCE(SUM(Duration_Seconds), 0) AS month_sec FROM StudySessions WHERE User_UID = ? AND Session_Date >= ? AND Duration_Seconds > 0", (user_uid, month_start))
    month_seconds = int(cursor.fetchone()["month_sec"])

    active_session = get_active_session(db_path, user_uid=user_uid)
    active_elapsed = int(active_session["elapsed_seconds"]) if (active_session and active_session.get("has_active")) else 0

    live_today_seconds = today_seconds + active_elapsed
    live_week_seconds = week_seconds + active_elapsed
    live_month_seconds = month_seconds + active_elapsed
    live_total_seconds = total_seconds + active_elapsed

    cursor.execute("SELECT COUNT(*) AS count FROM StudySessions WHERE User_UID = ? AND Duration_Seconds > 0", (user_uid,))
    total_sessions_count = int(cursor.fetchone()["count"])

    cursor.execute("SELECT COUNT(*) AS count FROM Tasks WHERE User_UID = ? AND Task_Status = 'Completed'", (user_uid,))
    completed_tasks_count = int(cursor.fetchone()["count"])

    cursor.execute("""
        SELECT COUNT(*) AS c, COALESCE(SUM(Total_Tracked_Seconds), 0) AS total_sec 
        FROM Tasks 
        WHERE User_UID = ? AND Task_Status = 'Completed' AND Total_Tracked_Seconds > 0
    """, (user_uid,))
    row = cursor.fetchone()
    completed_tracked_count = row["c"]
    completed_tracked_sec = row["total_sec"]
    avg_task_seconds = round(completed_tracked_sec / completed_tracked_count) if completed_tracked_count > 0 else 0

    cursor.execute("""
        SELECT COALESCE(t.Task_Subject, 'General / Unassigned') AS subject, 
               COALESCE(SUM(s.Duration_Seconds), 0) AS subject_sec,
               COUNT(DISTINCT t.Task_ID) as task_count
        FROM StudySessions s
        LEFT JOIN Tasks t ON s.Task_ID = t.Task_ID
        WHERE s.User_UID = ? AND s.Duration_Seconds > 0
        GROUP BY subject
        ORDER BY subject_sec DESC
    """, (user_uid,))
    subject_rows = cursor.fetchall()
    subject_breakdown = []
    for sr in subject_rows:
        sec = int(sr["subject_sec"])
        subject_breakdown.append({
            "subject": sr["subject"],
            "seconds": sec,
            "formatted": format_duration(sec),
            "percent": 0.0,
            "task_count": sr["task_count"]
        })

    if active_elapsed > 0 and active_session:
        active_subj = active_session.get("task_subject", "General")
        found = False
        for sb in subject_breakdown:
            if sb["subject"] == active_subj:
                sb["seconds"] += active_elapsed
                sb["formatted"] = format_duration(sb["seconds"])
                found = True
                break
        if not found and active_subj:
            subject_breakdown.append({
                "subject": active_subj,
                "seconds": active_elapsed,
                "formatted": format_duration(active_elapsed),
                "percent": 0.0,
                "task_count": 1
            })

    for sb in subject_breakdown:
        sb["percent"] = round((sb["seconds"] / live_total_seconds) * 100, 1) if live_total_seconds > 0 else 0

    cursor.execute("""
        SELECT s.Session_ID, s.Task_ID, s.Start_Time, s.End_Time, s.Duration_Seconds, 
               s.Session_Date, s.Status, s.Completed_At,
               COALESCE(t.Task_Title, 'Deep Focus Session') AS Task_Title,
               COALESCE(t.Task_Subject, 'General') AS Task_Subject
        FROM StudySessions s
        LEFT JOIN Tasks t ON s.Task_ID = t.Task_ID
        WHERE s.User_UID = ? AND s.Duration_Seconds > 0
        ORDER BY s.Session_ID DESC
        LIMIT 15
    """, (user_uid,))
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

    cursor.execute("""
        SELECT Task_ID, Task_Title, Task_Subject, Total_Tracked_Seconds, First_Tracked_At, Completed_At
        FROM Tasks
        WHERE User_UID = ? AND Task_Status = 'Completed' AND Total_Tracked_Seconds > 0
        ORDER BY Task_ID DESC
        LIMIT 10
    """, (user_uid,))
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
                cal_str = f"{days}d {hrs}h" if days > 0 else f"{max(1, hrs)}h"
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

    cursor.execute("""
        SELECT DISTINCT Session_Date FROM StudySessions WHERE User_UID = ? AND (Duration_Seconds > 0 OR Minutes_Spent > 0)
        UNION
        SELECT DISTINCT substr(Completed_At, 1, 10) FROM Tasks WHERE User_UID = ? AND Task_Status = 'Completed' AND Completed_At IS NOT NULL
        ORDER BY Session_Date DESC
    """, (user_uid, user_uid))
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

    insights = []
    if live_today_seconds > 0:
        insights.append(f"You recorded {format_duration(live_today_seconds)} of focused study time today.")
    else:
        insights.append("No study sessions recorded yet today. Click 'Start Tracking' on any study task to begin logging focused work.")

    if subject_breakdown:
        top_subj = subject_breakdown[0]
        insights.append(f"{top_subj['subject']} is your primary focus area, representing {top_subj['percent']}% of recorded focus time ({top_subj['formatted']}).")

    if completed_tracked_count > 0:
        insights.append(f"Your average actual completion time across {completed_tracked_count} completed task(s) is {format_duration(avg_task_seconds)}.")

    if streak_count >= 1:
        insights.append(f"🔥 Active Study Streak: You have maintained genuine study focus for {streak_count} consecutive day{'s' if streak_count != 1 else ''}!")

    return {
        "today_seconds": live_today_seconds,
        "today_completed_seconds": today_seconds,
        "today_formatted": format_duration(live_today_seconds),
        "week_seconds": live_week_seconds,
        "week_completed_seconds": week_seconds,
        "week_formatted": format_duration(live_week_seconds),
        "month_seconds": live_month_seconds,
        "month_completed_seconds": month_seconds,
        "month_formatted": format_duration(live_month_seconds),
        "total_seconds": live_total_seconds,
        "total_completed_seconds": total_seconds,
        "total_formatted": format_duration(live_total_seconds),
        "active_session": active_session,
        "active_elapsed_seconds": active_elapsed,
        "has_active_session": bool(active_session and active_session.get("has_active")),
        "total_sessions_count": total_sessions_count + (1 if active_elapsed > 0 else 0),
        "completed_tasks_count": completed_tasks_count,
        "avg_task_seconds": avg_task_seconds,
        "avg_task_formatted": format_duration(avg_task_seconds) if avg_task_seconds > 0 else "N/A",
        "streak_days": streak_count,
        "subject_breakdown": subject_breakdown,
        "recent_sessions": recent_sessions,
        "completed_analytics": completed_analytics,
        "insights": insights
    }


# =============================================================================
# User Profiles, Settings, Routines & Safe Legacy Migration
# =============================================================================

DAYS_ORDER = {
    "Monday": 1, "Tuesday": 2, "Wednesday": 3, "Thursday": 4,
    "Friday": 5, "Saturday": 6, "Sunday": 7, "Daily": 0,
}


def upsert_user_profile(uid: str, email: str, display_name: str, photo_url: str, db_path: str = DEFAULT_DB_PATH) -> bool:
    """Creates or updates user profile in SQLite. Returns True if first login."""
    now_iso = datetime.now().isoformat()
    conn = get_db_connection(db_path)
    with conn:
        cursor = conn.cursor()
        cursor.execute("SELECT User_UID FROM UserProfiles WHERE User_UID = ?", (uid,))
        existing = cursor.fetchone()
        is_new = existing is None
        if is_new:
            cursor.execute(
                "INSERT INTO UserProfiles (User_UID, Email, Display_Name, Photo_URL, Created_At, Last_Login_At) VALUES (?, ?, ?, ?, ?, ?)",
                (uid, email, display_name, photo_url, now_iso, now_iso)
            )
            cursor.execute(
                "INSERT OR IGNORE INTO UserSettings (User_UID, Max_Safe_Hours, Default_Focus_Minutes, Sound_Effects_Enabled, Updated_At) VALUES (?, 6.0, 25, 1, ?)",
                (uid, now_iso)
            )
        else:
            cursor.execute(
                "UPDATE UserProfiles SET Email = ?, Display_Name = ?, Photo_URL = ?, Last_Login_At = ? WHERE User_UID = ?",
                (email, display_name, photo_url, now_iso, uid)
            )
    conn.close()
    return is_new


def get_user_settings(uid: str, db_path: str = DEFAULT_DB_PATH) -> Dict[str, Any]:
    conn = get_db_connection(db_path)
    row = conn.execute("SELECT * FROM UserSettings WHERE User_UID = ?", (uid,)).fetchone()
    conn.close()
    if not row:
        return {"maxSafeHours": 6.0, "defaultFocusMinutes": 25, "soundEffectsEnabled": True}
    return {
        "maxSafeHours": float(row["Max_Safe_Hours"]),
        "defaultFocusMinutes": int(row["Default_Focus_Minutes"]),
        "soundEffectsEnabled": bool(row["Sound_Effects_Enabled"]),
    }


def update_user_settings(uid: str, max_safe_hours: float, default_focus_minutes: int, sound_effects_enabled: bool, db_path: str = DEFAULT_DB_PATH) -> Dict[str, Any]:
    safe_h = max(1.0, min(16.0, float(max_safe_hours)))
    focus_m = int(default_focus_minutes) if int(default_focus_minutes) in (15, 25, 45, 50) else 25
    snd = 1 if sound_effects_enabled else 0
    now_iso = datetime.now().isoformat()
    conn = get_db_connection(db_path)
    with conn:
        conn.execute(
            """
            INSERT INTO UserSettings (User_UID, Max_Safe_Hours, Default_Focus_Minutes, Sound_Effects_Enabled, Updated_At)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(User_UID) DO UPDATE SET
                Max_Safe_Hours = excluded.Max_Safe_Hours,
                Default_Focus_Minutes = excluded.Default_Focus_Minutes,
                Sound_Effects_Enabled = excluded.Sound_Effects_Enabled,
                Updated_At = excluded.Updated_At
            """,
            (uid, safe_h, focus_m, snd, now_iso)
        )
    conn.close()
    return {"maxSafeHours": safe_h, "defaultFocusMinutes": focus_m, "soundEffectsEnabled": bool(snd)}


def get_routines(uid: str, db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    rows = conn.execute("SELECT * FROM Routines WHERE User_UID = ?", (uid,)).fetchall()
    conn.close()
    routines = []
    for r in rows:
        routines.append({
            "Routine_ID": r["Routine_ID"],
            "title": r["Title"],
            "subject": r["Subject"],
            "dayOfWeek": r["Day_Of_Week"],
            "startTime": r["Start_Time"],
            "endTime": r["End_Time"],
            "focusGoal": r["Focus_Goal"] or "",
            "isActive": bool(r["Is_Active"]),
        })
    routines.sort(key=lambda x: (DAYS_ORDER.get(x["dayOfWeek"], 9), x["startTime"]))
    return routines


def add_routine(uid: str, title: str, subject: str, day_of_week: str, start_time: str, end_time: str, focus_goal: str = "", db_path: str = DEFAULT_DB_PATH) -> int:
    title = (title or "").strip()
    subject = (subject or "").strip() or "General"
    day_of_week = (day_of_week or "").strip()
    if not title or day_of_week not in DAYS_ORDER:
        raise ValueError("Please provide a valid routine title and day of week.")
    conn = get_db_connection(db_path)
    with conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO Routines (User_UID, Title, Subject, Day_Of_Week, Start_Time, End_Time, Focus_Goal, Is_Active, Created_At)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (uid, title, subject, day_of_week, (start_time or "17:00").strip(), (end_time or "18:00").strip(), (focus_goal or "").strip(), datetime.now().isoformat())
        )
        rid = cur.lastrowid
    conn.close()
    return rid


def toggle_routine(uid: str, routine_id: int, db_path: str = DEFAULT_DB_PATH) -> bool:
    conn = get_db_connection(db_path)
    with conn:
        row = conn.execute("SELECT Is_Active FROM Routines WHERE Routine_ID = ? AND User_UID = ?", (routine_id, uid)).fetchone()
        if not row:
            conn.close()
            return False
        new_val = 0 if row["Is_Active"] else 1
        conn.execute("UPDATE Routines SET Is_Active = ? WHERE Routine_ID = ? AND User_UID = ?", (new_val, routine_id, uid))
    conn.close()
    return True


def delete_routine(uid: str, routine_id: int, db_path: str = DEFAULT_DB_PATH) -> bool:
    conn = get_db_connection(db_path)
    with conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM Routines WHERE Routine_ID = ? AND User_UID = ?", (routine_id, uid))
        ok = cur.rowcount > 0
    conn.close()
    return ok


def get_legacy_migration_status(db_path: str = DEFAULT_DB_PATH) -> Dict[str, Any]:
    """Checks whether unclaimed __legacy__ tasks exist and have not yet been migrated/dismissed."""
    conn = get_db_connection(db_path)
    try:
        log = conn.execute("SELECT * FROM MigrationLog WHERE Id = 1").fetchone()
        if log and (log["Migrated_To_UID"] or log["Dismissed"]):
            return {"available": False, "legacy_count": 0, "migrated_to": log["Migrated_To_UID"]}
        row = conn.execute("SELECT COUNT(*) AS c FROM Tasks WHERE User_UID = '__legacy__'").fetchone()
        cnt = int(row["c"]) if row else 0
        return {"available": cnt > 0, "legacy_count": cnt, "migrated_to": None}
    finally:
        conn.close()


def migrate_legacy_data_to_user(uid: str, id_token: Optional[str] = None, db_path: str = DEFAULT_DB_PATH) -> int:
    """
    Safely associates unclaimed __legacy__ SQLite tasks/sessions with the first
    authenticated user after explicit confirmation, preventing duplicate migration.
    """
    status = get_legacy_migration_status(db_path)
    if not status["available"]:
        return 0

    conn = get_db_connection(db_path)
    migrated = 0
    try:
        legacy_tasks = conn.execute("SELECT * FROM Tasks WHERE User_UID = '__legacy__'").fetchall()
        if id_token:
            import firestore_store
            for row in legacy_tasks:
                t = dict(row)
                new_tid = firestore_store.add_task(
                    uid=uid,
                    id_token=id_token,
                    title=t["Task_Title"],
                    subject=t["Task_Subject"],
                    deadline=t["Task_Deadline"],
                    difficulty=t["Task_Difficulty"],
                    importance=t["Task_Importance"],
                    estimated_hours=t.get("Estimated_Hours"),
                    status=t.get("Task_Status", "Pending"),
                )
                subs = conn.execute("SELECT * FROM Subtasks WHERE Task_ID = ?", (t["Task_ID"],)).fetchall()
                for s in subs:
                    firestore_store.add_subtask(uid, id_token, new_tid, s["Subtask_Title"])
                migrated += 1
        else:
            with conn:
                conn.execute("UPDATE Tasks SET User_UID = ? WHERE User_UID = '__legacy__'", (uid,))
                conn.execute("UPDATE StudySessions SET User_UID = ? WHERE User_UID = '__legacy__'", (uid,))
                conn.execute("DELETE FROM ActiveSession WHERE User_UID = '__legacy__'")
                migrated = len(legacy_tasks)

        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO MigrationLog (Id, Migrated_To_UID, Migrated_At, Dismissed) VALUES (1, ?, ?, 0)",
                (uid, datetime.now().isoformat())
            )
    finally:
        conn.close()
    return migrated


def dismiss_legacy_migration(db_path: str = DEFAULT_DB_PATH) -> None:
    conn = get_db_connection(db_path)
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO MigrationLog (Id, Migrated_To_UID, Migrated_At, Dismissed) VALUES (1, NULL, ?, 1)",
            (datetime.now().isoformat(),)
        )
    conn.close()


def seed_sample_tasks(db_path: str = DEFAULT_DB_PATH, user_uid: str = "local_default") -> None:
    """Seeds the database with representative student tasks scoped to user_uid."""
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
            "deadline": (today - timedelta(days=1)).strftime("%Y-%m-%d"),
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
            db_path=db_path,
            user_uid=user_uid
        )
