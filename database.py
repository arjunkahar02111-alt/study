"""
Database management module for Smart Study Planner.
Handles SQLite relational database creation, task queries, updates, and transactions.
"""

import sqlite3
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any
from priority_calculator import (
    calculate_priority,
    calculate_urgency,
    calculate_workload,
    days_remaining,
    is_overdue,
    parse_date,
)

DEFAULT_DB_PATH = "study_planner.db"


def get_db_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Creates a connection to SQLite database with row factory for dictionary-like access."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initializes the database and creates the Tasks, Subtasks, and StudySessions tables."""
    conn = get_db_connection(db_path)
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS Tasks (
                Task_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                Task_Title TEXT NOT NULL,
                Task_Subject TEXT NOT NULL,
                Task_Deadline TEXT NOT NULL,
                Task_Difficulty INTEGER NOT NULL CHECK (Task_Difficulty BETWEEN 1 AND 5),
                Task_Importance INTEGER NOT NULL CHECK (Task_Importance BETWEEN 1 AND 5),
                Estimated_Hours REAL NOT NULL CHECK (Estimated_Hours > 0),
                Priority_Score REAL NOT NULL,
                Task_Status TEXT NOT NULL DEFAULT 'Pending' CHECK (Task_Status IN ('Pending', 'Completed'))
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS Subtasks (
                Subtask_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                Task_ID INTEGER NOT NULL,
                Subtask_Title TEXT NOT NULL,
                Is_Completed INTEGER NOT NULL DEFAULT 0 CHECK (Is_Completed IN (0, 1)),
                FOREIGN KEY (Task_ID) REFERENCES Tasks(Task_ID) ON DELETE CASCADE
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS StudySessions (
                Session_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                Task_ID INTEGER,
                Session_Date TEXT NOT NULL,
                Minutes_Spent INTEGER NOT NULL,
                Completed_At TEXT NOT NULL,
                FOREIGN KEY (Task_ID) REFERENCES Tasks(Task_ID) ON DELETE SET NULL
            );
        """)
    conn.close()


def add_task(
    title: str,
    subject: str,
    deadline: str,
    difficulty: int,
    importance: int,
    estimated_hours: float,
    status: str = "Pending",
    db_path: str = DEFAULT_DB_PATH
) -> int:
    """
    Validates task input, calculates priority score, and inserts task into database.
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
        hours_val = float(estimated_hours)
    except (ValueError, TypeError):
        raise ValueError("Invalid input")

    if not (1 <= diff_val <= 5) or not (1 <= imp_val <= 5) or hours_val <= 0:
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
                Priority_Score,
                Task_Status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title,
            subject,
            formatted_deadline,
            diff_val,
            imp_val,
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
    estimated_hours: float,
    status: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH
) -> bool:
    """
    Updates an existing task.
    Validates inputs and recalculates priority score.
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
        hours_val = float(estimated_hours)
    except (ValueError, TypeError):
        raise ValueError("Invalid input")

    if not (1 <= diff_val <= 5) or not (1 <= imp_val <= 5) or hours_val <= 0:
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
            priority_score,
            new_status,
            task_id
        ))
    conn.close()
    return True


def delete_task(task_id: int, db_path: str = DEFAULT_DB_PATH) -> bool:
    """Deletes a task by Task_ID."""
    existing = get_task_by_id(task_id, db_path)
    if not existing:
        return False

    conn = get_db_connection(db_path)
    with conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Tasks WHERE Task_ID = ?", (task_id,))
    conn.close()
    return True


def complete_task(task_id: int, db_path: str = DEFAULT_DB_PATH) -> bool:
    """Marks a task as 'Completed'."""
    existing = get_task_by_id(task_id, db_path)
    if not existing:
        return False

    conn = get_db_connection(db_path)
    with conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Tasks SET Task_Status = 'Completed' WHERE Task_ID = ?", (task_id,))
    conn.close()
    return True


def clear_all_tasks(db_path: str = DEFAULT_DB_PATH) -> None:
    """Removes all tasks from the database and resets the autoincrement ID counter to 1."""
    conn = get_db_connection(db_path)
    with conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Subtasks")
        cursor.execute("DELETE FROM StudySessions")
        cursor.execute("DELETE FROM Tasks")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('Tasks', 'Subtasks', 'StudySessions')")
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
    conn = get_db_connection(db_path)
    with conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO StudySessions (Task_ID, Session_Date, Minutes_Spent, Completed_At) VALUES (?, ?, ?, ?)",
            (task_id, today_str, minutes, now_str)
        )
        session_id = cursor.lastrowid
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
    workload_val = calculate_workload(task["Estimated_Hours"])

    task["is_overdue"] = overdue
    task["days_remaining"] = days_left
    task["urgency"] = urgency_val
    task["workload"] = workload_val

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
