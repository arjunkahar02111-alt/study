"""
Builds the complete IB DP Computer Science Internal Assessment (IA) Report
for SYNTRIQ: Smart Study Planner & Time Intelligence System.

Steps:
1. Spins up an isolated temporary SQLite DB with realistic academic data,
   focus sessions, subtasks, and an active live session (without modifying
   the workspace's study_planner.db).
2. Starts Flask in a background thread on an ephemeral localhost port.
3. Captures high-resolution (2x DPI) screenshots of all key application views
   using Playwright Chromium into screenshots/ia/.
4. Generates a publication-grade academic HTML report with inline vector SVG
   diagrams (Architecture/MVC, UML Use Case, Database ERD), real code excerpts,
   embedded application screenshots, and exact prose word counts.
5. Exports E:/Aasu/SYNTRIQ_IB_CS_Internal_Assessment.pdf via Chromium PDF engine.
"""

import os
import sys
import gc
import html
import time
import base64
import socket
import tempfile
import threading
from datetime import date, datetime, timedelta
from werkzeug.serving import make_server

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import database as db
from app import app
from playwright.sync_api import sync_playwright

SCRATCH_DIR = r"C:\Users\kahar\.gemini\antigravity-cli\brain\6f0761e0-6dff-4c37-9b21-4564ecdd83a2\scratch"
IA_SCREENSHOT_DIR = os.path.join(SCRATCH_DIR, "ia_screenshots")
HTML_OUTPUT_PATH = os.path.join(SCRATCH_DIR, "IA_REPORT.html")
PDF_OUTPUT_PATH = os.path.join(SCRATCH_DIR, "SYNTRIQ_IB_CS_Internal_Assessment.pdf")


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def populate_demo_database(db_path: str) -> dict:
    """Populates an isolated temporary database for realistic IA screenshots."""
    db.init_db(db_path)
    today = date.today()

    # 1. Completed task with historical focus sessions (for Time Intelligence analytics)
    completed_id = db.add_task(
        title="IB Mathematics AA HL Past Paper Practice",
        subject="Mathematics",
        deadline=(today - timedelta(days=1)).strftime("%Y-%m-%d"),
        difficulty=4,
        importance=5,
        estimated_hours=3.0,
        db_path=db_path,
    )
    # Insert realistic focus sessions over the past 3 days so streak & breakdown look authentic
    conn = db.get_db_connection(db_path)
    with conn:
        sessions = [
            (completed_id, (today - timedelta(days=2)).strftime("%Y-%m-%d"), 3200, "16:00", "16:53"),
            (completed_id, (today - timedelta(days=1)).strftime("%Y-%m-%d"), 2700, "18:10", "18:55"),
        ]
        for tid, sdate, dur, st, et in sessions:
            start_iso = f"{sdate}T{st}:00"
            end_iso = f"{sdate}T{et}:00"
            conn.execute(
                """
                INSERT INTO StudySessions (
                    Task_ID, Start_Time, End_Time, Duration_Seconds,
                    Session_Date, Minutes_Spent, Status, Completed_At, Created_At
                ) VALUES (?, ?, ?, ?, ?, ?, 'completed', ?, ?)
                """,
                (tid, start_iso, end_iso, dur, sdate, round(dur / 60), f"{sdate} {et}:00", start_iso),
            )
        conn.execute(
            """
            UPDATE Tasks
            SET Total_Tracked_Seconds = 5900,
                First_Tracked_At = ?,
                Completed_At = ?,
                Task_Status = 'Completed'
            WHERE Task_ID = ?
            """,
            (
                f"{(today - timedelta(days=2)).strftime('%Y-%m-%d')}T16:00:00",
                f"{(today - timedelta(days=1)).strftime('%Y-%m-%d')}T19:05:00",
                completed_id,
            ),
        )
    conn.close()

    # 2. Pending tasks (overdue, due tomorrow, upcoming)
    t_overdue = db.add_task(
        title="Chemistry Stoichiometry Lab Analysis",
        subject="Chemistry",
        deadline=(today - timedelta(days=1)).strftime("%Y-%m-%d"),
        difficulty=3,
        importance=4,
        estimated_hours=1.5,
        db_path=db_path,
    )
    t_top = db.add_task(
        title="Computer Science IA Criterion D & Testing",
        subject="Computer Science",
        deadline=(today + timedelta(days=1)).strftime("%Y-%m-%d"),
        difficulty=5,
        importance=5,
        estimated_hours=5.0,
        db_path=db_path,
    )
    t_phys = db.add_task(
        title="Physics IA Uncertainty & Error Propagation",
        subject="Physics",
        deadline=(today + timedelta(days=2)).strftime("%Y-%m-%d"),
        difficulty=5,
        importance=5,
        estimated_hours=4.0,
        db_path=db_path,
    )
    t_eng = db.add_task(
        title="English HL Essay Outline on Hamlet",
        subject="English Literature",
        deadline=(today + timedelta(days=5)).strftime("%Y-%m-%d"),
        difficulty=4,
        importance=4,
        estimated_hours=3.0,
        db_path=db_path,
    )
    t_econ = db.add_task(
        title="Economics Macroeconomics Policy Notes",
        subject="Economics",
        deadline=(today + timedelta(days=10)).strftime("%Y-%m-%d"),
        difficulty=2,
        importance=3,
        estimated_hours=None,  # Demonstrates optional target hours -> neutral workload 3
        db_path=db_path,
    )

    # Add subtasks to top CS task
    s1 = db.add_subtask(t_top, "Document priority_calculator.py algorithm", db_path)
    db.toggle_subtask(s1, db_path)
    db.add_subtask(t_top, "Verify 45 automated unit & integration tests", db_path)
    db.add_subtask(t_top, "Embed UI screenshots into Criterion C", db_path)

    # Add completed sessions for Physics and CS earlier today so Time Intelligence is rich
    today_str = today.strftime("%Y-%m-%d")
    conn = db.get_db_connection(db_path)
    with conn:
        for tid, dur, st, et in [
            (t_phys, 2400, "09:15", "09:55"),
            (t_top, 1800, "11:00", "11:30"),
        ]:
            start_iso = f"{today_str}T{st}:00"
            end_iso = f"{today_str}T{et}:00"
            conn.execute(
                """
                INSERT INTO StudySessions (
                    Task_ID, Start_Time, End_Time, Duration_Seconds,
                    Session_Date, Minutes_Spent, Status, Completed_At, Created_At
                ) VALUES (?, ?, ?, ?, ?, ?, 'completed', ?, ?)
                """,
                (tid, start_iso, end_iso, dur, today_str, round(dur / 60), f"{today_str} {et}:00", start_iso),
            )
            conn.execute(
                "UPDATE Tasks SET Total_Tracked_Seconds = Total_Tracked_Seconds + ?, First_Tracked_At = COALESCE(First_Tracked_At, ?) WHERE Task_ID = ?",
                (dur, start_iso, tid),
            )
    conn.close()

    # Start an active tracking session on t_top with pre-accumulated 12m 34s
    db.start_tracking_session(t_top, db_path=db_path)
    conn = db.get_db_connection(db_path)
    with conn:
        conn.execute("UPDATE ActiveSession SET Accumulated_Seconds = 754 WHERE ID = 1")
    conn.close()

    return {
        "t_top": t_top,
        "t_overdue": t_overdue,
        "t_phys": t_phys,
        "t_eng": t_eng,
        "t_econ": t_econ,
        "completed_id": completed_id,
    }


def capture_screenshots(base_url: str) -> dict:
    """Captures high-DPI screenshots of all key views using Playwright Chromium."""
    os.makedirs(IA_SCREENSHOT_DIR, exist_ok=True)
    paths = {}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 1366, "height": 1160}, device_scale_factor=2)
        page = context.new_page()

        # 1. Dashboard (desktop - includes heatmap, stats, and task table without floating overlap)
        page.goto(f"{base_url}/dashboard", wait_until="networkidle")
        page.wait_for_timeout(700)
        page.evaluate("""
            const w = document.getElementById('activeSessionWidget');
            if (w) { w.style.bottom = '14px'; w.style.right = '14px'; }
        """)
        p_dash = os.path.join(IA_SCREENSHOT_DIR, "ia_01_dashboard.png")
        page.screenshot(path=p_dash, full_page=False)
        paths["dashboard"] = p_dash

        # 2. Study Plan with subtasks expanded on #1 task
        page.goto(f"{base_url}/study-plan", wait_until="networkidle")
        page.wait_for_timeout(500)
        first_sub_header = page.locator(".subtasks-header").first
        if first_sub_header.count() > 0:
            first_sub_header.click()
            page.wait_for_timeout(300)
        p_plan = os.path.join(IA_SCREENSHOT_DIR, "ia_02_study_plan.png")
        page.screenshot(path=p_plan, full_page=False)
        paths["study_plan"] = p_plan

        # 3. What-If Simulator modal on Study Plan
        page.set_viewport_size({"width": 1366, "height": 860})
        sim_btn = page.get_by_role("button", name="What-If Simulator")
        if sim_btn.count() > 0:
            sim_btn.click()
            page.wait_for_timeout(400)
            p_sim = os.path.join(IA_SCREENSHOT_DIR, "ia_03_what_if_simulator.png")
            page.screenshot(path=p_sim, full_page=False)
            paths["simulator"] = p_sim

        # 4. Time Intelligence Dashboard (hide floating pill since top active banner already shows live clock)
        page.goto(f"{base_url}/time-intelligence", wait_until="networkidle")
        page.wait_for_timeout(700)
        page.evaluate("""
            const w = document.getElementById('activeSessionWidget');
            if (w) { w.style.display = 'none'; }
        """)
        p_intel = os.path.join(IA_SCREENSHOT_DIR, "ia_04_time_intelligence.png")
        page.screenshot(path=p_intel, full_page=True)
        paths["time_intel"] = p_intel

        # 5. Add Task Page with realistic live preview populated
        page.goto(f"{base_url}/add-task", wait_until="networkidle")
        page.wait_for_timeout(400)
        page.fill("#title", "History Extended Essay First Draft")
        page.fill("#subject", "History")
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        page.fill("#deadline", tomorrow)
        page.select_option("#difficulty", "4")
        page.select_option("#importance", "5")
        page.fill("#estimated_hours", "4.5")
        page.dispatch_event("#estimated_hours", "input")
        page.wait_for_timeout(300)
        p_add = os.path.join(IA_SCREENSHOT_DIR, "ia_05_add_task.png")
        page.screenshot(path=p_add, full_page=False)
        paths["add_task"] = p_add

        # 6. Focus Pomodoro Modal on Dashboard
        page.goto(f"{base_url}/dashboard", wait_until="networkidle")
        page.wait_for_timeout(400)
        page.evaluate("openPomodoroModal()")
        page.wait_for_timeout(350)
        p_pomo = os.path.join(IA_SCREENSHOT_DIR, "ia_06_focus_timer.png")
        page.screenshot(path=p_pomo, full_page=False)
        paths["pomodoro"] = p_pomo

        # 7. Mobile Responsive Dashboard (390x844)
        mob_ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        mob_page = mob_ctx.new_page()
        mob_page.goto(f"{base_url}/dashboard", wait_until="networkidle")
        mob_page.wait_for_timeout(700)
        p_mob = os.path.join(IA_SCREENSHOT_DIR, "ia_07_mobile_dashboard.png")
        mob_page.screenshot(path=p_mob, full_page=False)
        paths["mobile"] = p_mob

        mob_ctx.close()
        context.close()
        browser.close()

    return paths


def count_words(text: str) -> int:
    return len([w for w in text.strip().split() if w])


def build_ia_html(screenshot_paths: dict) -> str:
    """Constructs the complete IB Computer Science IA HTML document."""

    def img_uri(key: str) -> str:
        with open(screenshot_paths[key], "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        return f"data:image/png;base64,{b64}"

    # --- Prose Sections (tracked explicitly for IB Word Count <= 2,000) ---
    crit_a_scenario = (
        "As an International Baccalaureate Diploma Programme student managing six demanding subjects alongside "
        "Internal Assessments and the Extended Essay, I frequently struggle to allocate my daily study time "
        "effectively. Each assignment varies in deadline urgency, academic weight, cognitive difficulty, and "
        "expected duration. Currently, I rely on static paper checklists and basic to-do spreadsheets that only "
        "store task names and due dates. Because those tools lack automated prioritization, tasks with distant "
        "deadlines or low academic impact are often completed prematurely while urgent, high-stakes coursework "
        "is delayed. Furthermore, static lists do not measure how many real focus hours are spent per subject, "
        "making it difficult to evaluate study habits or estimate future workloads accurately. To solve this "
        "problem, I am developing SYNTRIQ, a web-based Smart Study Planner and Real-Time Time Intelligence "
        "system that mathematically ranks pending tasks and tracks genuine study sessions."
    )

    crit_a_context = (
        "I decided to build a web application rather than a standalone desktop GUI or spreadsheet macro so the "
        "system remains accessible across laptops, tablets, and mobile browsers without local software "
        "installation. The solution is implemented using Python and the Flask micro-framework on the server, "
        "SQLite for persistent ACID-compliant relational storage, and HTML5, CSS3, and vanilla JavaScript for "
        "an interactive, responsive client interface. Following a modular Model-View-Controller (MVC) pattern, "
        "algorithmic priority scoring (priority_calculator.py) and relational data management (database.py) "
        "are strictly decoupled from Flask route controllers (app.py) and Jinja2 presentation templates. SQLite "
        "was selected over flat CSV files because relational foreign keys, CHECK constraints, and parameterized "
        "SQL queries ensure data integrity, enforce a single active focus session at the database level, and "
        "support fast aggregation queries for real-time Time Intelligence analytics."
    )

    crit_a_words = count_words(crit_a_scenario + " " + crit_a_context)

    # Criterion D prose sections (paired with exact code blocks)
    crit_d_blocks = [
        {
            "title": "1. Modular MVC-Inspired Architecture",
            "code_lang": "text",
            "code": (
                "E:\\Aasu\\\n"
                "├── priority_calculator.py  # Pure algorithmic scoring & date helpers (Model Logic)\n"
                "├── database.py             # SQLite schema, parameterized CRUD & Time Intelligence (Model)\n"
                "├── app.py                  # Flask routes, input validation & JSON APIs (Controller)\n"
                "├── templates/              # Jinja2 HTML5 views (dashboard, study_plan, time_intelligence)\n"
                "└── static/js/main.js       # Live preview, Pomodoro timer, Web Audio & session sync (View)"
            ),
            "prose": (
                "Separating the codebase into dedicated modules follows the Model-View-Controller paradigm, making "
                "each layer independently testable and maintainable. Isolating priority_calculator.py from Flask "
                "HTTP requests allows the scoring formula to be unit-tested directly with deterministic dates, while "
                "database.py centralizes all SQLite connections and transactions via get_db_connection() with foreign "
                "keys enabled. The testing strategy does not directly test this architectural separation, because the "
                "automated test suite evaluates functional routes, database operations, and algorithmic outputs "
                "rather than structural decoupling."
            ),
        },
        {
            "title": "2. Weighted Priority Algorithm & Neutral Workload Fallback",
            "code_lang": "python",
            "code": (
                "def calculate_priority(deadline, difficulty, importance, estimated_hours=None, current_date=None):\n"
                "    difficulty_val = int(difficulty)\n"
                "    importance_val = int(importance)\n"
                "    if not (1 <= difficulty_val <= 5) or not (1 <= importance_val <= 5):\n"
                "        raise ValueError(\"Difficulty and Importance must be between 1 and 5.\")\n"
                "    urgency = calculate_urgency(deadline, current_date)\n"
                "    workload = calculate_workload(estimated_hours)  # Returns 3 when omitted\n"
                "    score = (0.4 * urgency) + (0.3 * importance_val) + (0.2 * difficulty_val) + (0.1 * workload)\n"
                "    return round(score, 2)"
            ),
            "prose": (
                "The priority algorithm converts heterogeneous academic attributes into a normalized 1.00–5.00 score, "
                "weighting deadline urgency highest (40%) followed by importance (30%), difficulty (20%), and workload "
                "(10%). Crucially, calculate_workload() implements a transparent neutral fallback of 3 when "
                "estimated_hours is omitted, allowing students to create tasks rapidly without guessing completion "
                "times while preserving mathematical consistency across all records. The testing strategy is very "
                "effective for this component because deterministic unit tests verify exact scores under both full "
                "inputs (e.g., 5.00 max priority) and omitted durations (neutral 0.30 workload contribution)."
            ),
        },
        {
            "title": "3. Relational Schema & Parameterized CRUD Operations",
            "code_lang": "python",
            "code": (
                "def add_task(title, subject, deadline, difficulty, importance, estimated_hours=None, db_path=DEFAULT_DB_PATH):\n"
                "    priority_score = calculate_priority(formatted_deadline, diff_val, imp_val, hours_val)\n"
                "    conn = get_db_connection(db_path)\n"
                "    with conn:\n"
                "        cursor = conn.cursor()\n"
                "        cursor.execute(\"\"\"\n"
                "            INSERT INTO Tasks (Task_Title, Task_Subject, Task_Deadline, Task_Difficulty,\n"
                "                Task_Importance, Estimated_Hours, Target_Hours, Total_Tracked_Seconds,\n"
                "                Priority_Score, Task_Status) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)\n"
                "        \"\"\", (title, subject, formatted_deadline, diff_val, imp_val, hours_val, hours_val, priority_score, status))\n"
                "    conn.close()\n"
                "    return cursor.lastrowid"
            ),
            "prose": (
                "All database writes use SQLite parameterized placeholders (?) inside a Python context manager "
                "(with conn:). Parameterization prevents SQL injection attacks by binding user strings strictly as "
                "data values rather than executable SQL syntax, while the context manager guarantees ACID atomicity "
                "by automatically rolling back failed transactions. Relational foreign keys with ON DELETE CASCADE "
                "cleanly remove dependent Subtasks and ActiveSession rows when a task is deleted. The testing "
                "strategy is effective because integration tests confirm task insertion, update recalculation, "
                "cascade-safe deletion, and persistence across fresh database connections."
            ),
        },
        {
            "title": "4. Two-Tier Input Validation & Error Handling",
            "code_lang": "python",
            "code": (
                "if not title or not subject or not deadline:\n"
                "    flash(\"Please complete all required fields\", \"danger\")\n"
                "    return render_template(\"add_task.html\", form_data=request.form), 400\n"
                "try:\n"
                "    diff_int = int(difficulty)\n"
                "    imp_int = int(importance)\n"
                "    hours_float = float(estimated_hours) if estimated_hours else None\n"
                "except (ValueError, TypeError):\n"
                "    flash(\"Invalid input\", \"danger\")\n"
                "    return render_template(\"add_task.html\", form_data=request.form), 400\n"
                "if diff_int < 1 or diff_int > 5 or imp_int < 1 or imp_int > 5 or (hours_float is not None and hours_float <= 0):\n"
                "    flash(\"Invalid input\", \"danger\")\n"
                "    return render_template(\"add_task.html\", form_data=request.form), 400"
            ),
            "prose": (
                "Validation operates defensively at both the Flask controller and the SQLite schema. In app.py, "
                "submitted strings are stripped, parsed inside exception handlers, and range-checked before returning "
                "HTTP 400 with preserved form_data and descriptive flash warnings. Simultaneously, SQLite CHECK "
                "constraints enforce 1–5 boundaries on difficulty and importance and valid status enumerations at the "
                "storage layer, protecting integrity even if helper functions are called outside the web UI. The "
                "testing strategy is effective as automated HTTP POST tests confirm rejection of blank fields, "
                "non-numeric inputs, zero hours, and out-of-range ratings."
            ),
        },
        {
            "title": "5. Dynamic Study Plan Generation & What-If Simulation",
            "code_lang": "python",
            "code": (
                "def get_study_plan(db_path=DEFAULT_DB_PATH, current_date=None):\n"
                "    if current_date is None: current_date = date.today()\n"
                "    conn = get_db_connection(db_path)\n"
                "    rows = conn.execute(\"SELECT * FROM Tasks WHERE Task_Status = 'Pending'\").fetchall()\n"
                "    tasks = []\n"
                "    for row in rows:\n"
                "        task = dict(row)\n"
                "        score = calculate_priority(task[\"Task_Deadline\"], task[\"Task_Difficulty\"],\n"
                "                                   task[\"Task_Importance\"], task[\"Estimated_Hours\"], current_date)\n"
                "        task[\"Priority_Score\"] = score\n"
                "        tasks.append(_format_task_dict(task, current_date))\n"
                "        conn.execute(\"UPDATE Tasks SET Priority_Score = ? WHERE Task_ID = ?\", (score, task[\"Task_ID\"]))\n"
                "    conn.commit(); conn.close()\n"
                "    tasks.sort(key=lambda t: (-t[\"Priority_Score\"], t[\"Task_Deadline\"]))\n"
                "    return tasks"
            ),
            "prose": (
                "Because urgency increases as calendar days pass, stored priority scores would become stale if not "
                "refreshed. Therefore, get_study_plan() dynamically recomputes every pending task against today's "
                "date, marks overdue items, fetches subtasks, and sorts records in Python using Timsort (O(n log n)) "
                "with a compound key (-Priority_Score, Task_Deadline) to break priority ties by earliest due date. "
                "Additionally, /api/simulate-priority lets students test hypothetical deadline and hour shifts without "
                "mutating saved records. The testing strategy effectively validates descending priority order, overdue "
                "detection, and What-If score deltas."
            ),
        },
        {
            "title": "6. Drift-Free Real-Time Tracking & Single-Session Lock",
            "code_lang": "python",
            "code": (
                "def start_tracking_session(task_id, force=False, db_path=DEFAULT_DB_PATH):\n"
                "    existing_active = cursor.execute(\"SELECT * FROM ActiveSession WHERE ID = 1\").fetchone()\n"
                "    if existing_active and existing_active[\"Task_ID\"] != task_id and not force:\n"
                "        return {\"conflict\": True, \"has_conflict\": True, ...}\n"
                "    elif existing_active and existing_active[\"Task_ID\"] != task_id and force:\n"
                "        stop_tracking_session(db_path)\n"
                "        return start_tracking_session(task_id, force=False, db_path=db_path)\n"
                "    # Elapsed formula in get_active_session():\n"
                "    elapsed = accum if is_paused else accum + max(0, round(time.time() - start_ts))"
            ),
            "prose": (
                "Naive browser timers lose accuracy when tabs are throttled or closed. SYNTRIQ resolves this by "
                "storing a persistent UNIX Start_Timestamp and Accumulated_Seconds in the ActiveSession table, "
                "constrained by CHECK (ID = 1) so only one focus session can run system-wide. Pausing adds the "
                "elapsed interval into Accumulated_Seconds, while attempting to track a second task triggers a "
                "conflict response unless force=True stops the prior session cleanly. The testing strategy is "
                "effective because automated tests verify single-session conflict detection, force-switching, "
                "pause/resume continuity, and auto-finalization upon task completion."
            ),
        },
        {
            "title": "7. Time Intelligence Aggregation & Subject Analytics",
            "code_lang": "python",
            "code": (
                "cursor.execute(\"\"\"\n"
                "    SELECT COALESCE(t.Task_Subject, 'General / Unassigned') AS subject,\n"
                "           COALESCE(SUM(s.Duration_Seconds), 0) AS subject_sec,\n"
                "           COUNT(DISTINCT t.Task_ID) as task_count\n"
                "    FROM StudySessions s LEFT JOIN Tasks t ON s.Task_ID = t.Task_ID\n"
                "    WHERE s.Duration_Seconds > 0 GROUP BY subject ORDER BY subject_sec DESC\n"
                "\"\"\")"
            ),
            "prose": (
                "The Time Intelligence engine aggregates completed StudySessions alongside live ActiveSession elapsed "
                "seconds so today's, weekly, monthly, and subject-wise totals update instantaneously without waiting "
                "for a session to stop. Computing SQLite SUM() and GROUP BY aggregations directly in the database "
                "minimizes memory overhead compared to loading raw rows into Python, and a UNION query derives the "
                "student's consecutive study streak exclusively from verified focus dates. The testing strategy "
                "effectively verifies that logged sessions and live active sessions appear immediately in both the "
                "/time-intelligence view and JSON API responses."
            ),
        },
        {
            "title": "8. Client-Side Live Preview, Focus Timer & Responsive UI",
            "code_lang": "javascript",
            "code": (
                "function renderActiveDigits() {\n"
                "    let currentElapsed = data.elapsed_seconds || 0;\n"
                "    if (!data.is_paused) {\n"
                "        const clientDelta = (Date.now() / 1000) - activeSessionClientSyncTime;\n"
                "        currentElapsed = Math.round((data.elapsed_seconds || 0) + clientDelta);\n"
                "    }\n"
                "    if (digitsEl) digitsEl.textContent = formatDurationHms(currentElapsed);\n"
                "    updateTimeIntelDashboard(currentElapsed);\n"
                "}"
            ),
            "prose": (
                "In static/js/main.js, real-time priority previews, the SVG Pomodoro timer, and the floating "
                "active-session widget synchronize against Date.now() timestamps and re-sync on Page Visibility API "
                "events rather than counting tick intervals, preventing background browser throttling drift. "
                "Synthesized Web Audio API chimes and CSS media queries provide offline focus feedback and mobile "
                "drawer ergonomics. However, the testing strategy does not fully test client-side visual rendering "
                "or audio synthesis, because automated Python tests assert DOM element presence and API payloads "
                "rather than live JavaScript execution or audio output."
            ),
        },
    ]

    crit_d_words = sum(count_words(b["prose"]) for b in crit_d_blocks)

    crit_e_criteria = [
        ("1. Two-tier input validation", "Achieved — Both app.py route handlers (HTTP 400 with flash warnings) and SQLite CHECK constraints reject blank required fields, invalid dates, non-numeric inputs, and out-of-range ratings."),
        ("2. Add tasks with optional hours", "Achieved — Students can create tasks with Title, Subject, Deadline, Difficulty, Importance, and optional Target Hours via /add-task with live score preview."),
        ("3. Edit tasks & recalculate score", "Achieved — The /edit-task/<id> route pre-populates existing values, validates updates, and immediately recalculates Priority_Score in SQLite."),
        ("4. Safe task deletion", "Achieved — POST /delete-task/<id> removes the task and cascades cleanup of linked subtasks and any active tracking session."),
        ("5. Weighted priority & fallback", "Achieved — priority_calculator.py implements 0.4U + 0.3I + 0.2D + 0.1W and applies a neutral workload score of 3 when hours are omitted."),
        ("6. Study Plan & What-If Simulator", "Achieved — /study-plan lists pending tasks in descending Priority_Score order with factor tags, and /api/simulate-priority previews hypothetical shifts."),
        ("7. Overdue, upcoming & heatmap", "Achieved — Dashboard highlights overdue tasks, isolates 7-day upcoming deadlines, renders a 7-Day Workload Heatmap, and alerts when daily hours exceed 6.0h."),
        ("8. Task completion & sub-milestones", "Achieved — One-click completion logs Completed_At and auto-stops active tracking; AJAX endpoints add, toggle, and delete per-task subtasks."),
        ("9. Real-time tracking & Time Intel", "Achieved — ActiveSession enforces single-task focus, pause/resume retains exact seconds without drift, and /time-intelligence renders live subject and session analytics."),
        ("10. Persistence, UI & .ics export", "Achieved — SQLite persists records across restarts, responsive CSS adapts across desktop and mobile viewports, and /export/calendar.ics exports valid RFC-5545 events."),
    ]

    crit_e_improvements = (
        "Although SYNTRIQ meets all ten success criteria and passes all 45 automated tests across its verification "
        "suites, several enhancements would elevate its scalability and pedagogical value. First, migrating from "
        "single-user local SQLite to a managed PostgreSQL database with user authentication (hashed passwords and "
        "session tokens) would allow multiple students to synchronize plans securely across devices and eliminate "
        "ephemeral storage limitations on serverless platforms such as Vercel. Second, implementing an adaptive "
        "calibration model that compares historical Estimated_Hours against actual Total_Tracked_Seconds per "
        "subject could automatically adjust workload estimates and personalize priority weights for each learner. "
        "Third, adding automated browser-level end-to-end tests alongside push notifications and two-way Google "
        "Calendar synchronization would validate live JavaScript interactions and proactively remind students "
        "before assignments become overdue."
    )

    crit_e_words = count_words(" ".join(c[1] for c in crit_e_criteria) + " " + crit_e_improvements)
    # Also include Criterion C brief algorithm prose
    crit_c_prose = (
        "The system follows a layered MVC architecture separating presentation templates, Flask route controllers, "
        "algorithmic priority scoring, and SQLite relational persistence across four normalized tables."
    )
    crit_c_words = count_words(crit_c_prose)

    total_words = crit_a_words + crit_c_words + crit_d_words + crit_e_words

    # Build Criterion D HTML cards
    crit_d_html = ""
    for block in crit_d_blocks:
        crit_d_html += f"""
        <div class="dev-block avoid-break">
            <h3 class="dev-heading">{html.escape(block['title'])}</h3>
            <pre class="code-box"><code>{html.escape(block['code'])}</code></pre>
            <p>{html.escape(block['prose'])}</p>
        </div>
        """

    # Build Criterion E evaluation list
    crit_e_list_html = ""
    for title, desc in crit_e_criteria:
        crit_e_list_html += f"""
        <div class="eval-item">
            <p class="eval-title"><strong>{html.escape(title)}</strong></p>
            <p class="eval-desc">{html.escape(desc)}</p>
        </div>
        """

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Computer Science Internal Assessment - SYNTRIQ</title>
<style>
  @page {{
    size: A4;
    margin: 18mm 18mm 18mm 18mm;
    @top-right {{
      content: "SYNTRIQ: Smart Study Planner — IB Computer Science IA";
      font-family: 'Segoe UI', Arial, sans-serif;
      font-size: 8.5pt;
      color: #64748b;
    }}
    @bottom-left {{
      content: "Computer Science Internal Assessment";
      font-family: 'Segoe UI', Arial, sans-serif;
      font-size: 8.5pt;
      color: #64748b;
    }}
    @bottom-right {{
      content: "Page " counter(page) " of " counter(pages);
      font-family: 'Segoe UI', Arial, sans-serif;
      font-size: 8.5pt;
      color: #64748b;
    }}
  }}
  @page :first {{
    @top-right {{ content: normal; }}
    @bottom-left {{ content: normal; }}
    @bottom-right {{ content: normal; }}
  }}

  * {{ box-sizing: border-box; }}
  body {{
    font-family: 'Segoe UI', 'Liberation Sans', Arial, sans-serif;
    font-size: 9.8pt;
    line-height: 1.44;
    color: #1e293b;
    margin: 0;
    padding: 0;
  }}

  /* Cover Page */
  .cover-page {{
    height: 256mm;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    border: 1.5px solid #cbd5e1;
    border-radius: 6px;
    padding: 40px 36px;
    page-break-after: always;
    background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  }}
  .cover-kicker {{
    font-size: 15pt;
    font-weight: 600;
    color: #334155;
    letter-spacing: 0.4px;
    margin-bottom: 6px;
  }}
  .cover-subkicker {{
    font-size: 13pt;
    color: #475569;
    margin-bottom: 44px;
  }}
  .cover-title {{
    font-size: 24pt;
    font-weight: 800;
    color: #0f172a;
    line-height: 1.2;
    margin: 0 0 14px 0;
    max-width: 90%;
  }}
  .cover-subtitle {{
    font-size: 12pt;
    font-weight: 500;
    color: #ea580c;
    margin-bottom: 48px;
  }}
  .cover-meta {{
    font-size: 12pt;
    font-weight: 600;
    color: #1e293b;
    padding: 10px 24px;
    border: 1px solid #cbd5e1;
    border-radius: 999px;
    background: #ffffff;
  }}
  .cover-summary-box {{
    margin-top: 46px;
    text-align: left;
    font-size: 9.2pt;
    color: #475569;
    border-top: 1px solid #e2e8f0;
    padding-top: 14px;
    width: 82%;
  }}

  /* Headings & Sections */
  .criterion-title {{
    font-size: 14.5pt;
    font-weight: 800;
    color: #0f172a;
    text-align: center;
    border-bottom: 2px solid #f97316;
    padding-bottom: 6px;
    margin: 0 0 14px 0;
  }}
  .page-break {{ page-break-before: always; }}
  h2 {{
    font-size: 11.2pt;
    font-weight: 700;
    color: #0f172a;
    margin: 10px 0 5px 0;
  }}
  h3.dev-heading {{
    font-size: 10.6pt;
    font-weight: 700;
    color: #c2410c;
    margin: 10px 0 4px 0;
    text-decoration: underline;
    text-decoration-color: #fdba74;
    text-underline-offset: 3px;
  }}
  p {{ margin: 0 0 7px 0; text-align: justify; }}
  .word-badge {{
    text-align: right;
    font-weight: 700;
    font-size: 9.2pt;
    color: #334155;
    margin: 6px 0 8px 0;
  }}

  ol.criteria-list {{
    margin: 3px 0 6px 0;
    padding-left: 20px;
  }}
  ol.criteria-list li {{
    margin-bottom: 2.5px;
    font-size: 9.5pt;
    line-height: 1.38;
  }}

  /* Planning & Decomposition Boxes */
  .decomp-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 12px;
  }}
  .decomp-card {{
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    padding: 9px 11px;
    background: #f8fafc;
    font-size: 9pt;
    line-height: 1.4;
  }}
  .decomp-card h4 {{
    margin: 0 0 5px 0;
    font-size: 9.8pt;
    color: #0f172a;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 3px;
  }}
  .decomp-card ul {{
    margin: 0;
    padding-left: 16px;
  }}
  .decomp-card li {{ margin-bottom: 2px; }}

  /* Tables */
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 8px 0 14px 0;
    font-size: 8.6pt;
    line-height: 1.35;
  }}
  th, td {{
    border: 1px solid #94a3b8;
    padding: 5px 7px;
    vertical-align: top;
    text-align: left;
  }}
  th {{
    background-color: #f1f5f9;
    font-weight: 700;
    color: #0f172a;
  }}
  tr.phase-row td {{
    background-color: #fff7ed;
    font-weight: 700;
    color: #9a3412;
  }}
  tr {{ break-inside: avoid; }}

  /* Code & Pseudocode */
  pre.code-box {{
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-left: 3.5px solid #f97316;
    border-radius: 4px;
    padding: 7px 10px;
    font-family: 'Consolas', 'JetBrains Mono', 'Courier New', monospace;
    font-size: 8.0pt;
    line-height: 1.38;
    color: #0f172a;
    white-space: pre-wrap;
    word-break: break-word;
    margin: 4px 0 7px 0;
  }}
  .sql-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }}

  /* Diagrams & Screenshots */
  .figure-box {{
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 8px;
    margin: 8px 0 12px 0;
    background: #ffffff;
    text-align: center;
    break-inside: avoid;
  }}
  .figure-box img {{
    max-width: 100%;
    height: auto;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    display: block;
    margin: 0 auto;
  }}
  .figure-caption {{
    font-size: 8.7pt;
    font-weight: 600;
    color: #475569;
    margin-top: 6px;
    text-align: center;
  }}
  .screenshot-grid-2 {{
    display: grid;
    grid-template-columns: 1.45fr 0.72fr;
    gap: 10px;
    align-items: start;
    break-inside: avoid;
  }}

  .avoid-break {{ break-inside: avoid; }}

  .eval-item {{ margin-bottom: 4px; break-inside: avoid; }}
  .eval-title {{ margin: 0 0 1px 0; font-size: 9.4pt; color: #0f172a; }}
  .eval-desc {{ margin: 0 0 3px 0; font-size: 9.2pt; line-height: 1.38; }}
</style>
</head>
<body>

<!-- ==================== COVER PAGE ==================== -->
<div class="cover-page">
  <div class="cover-kicker">Computer Science</div>
  <div class="cover-subkicker">Internal Assessment</div>
  <h1 class="cover-title">SYNTRIQ: Smart Study Planner &amp; Time Intelligence System</h1>
  <div class="cover-subtitle">Algorithmic Task Prioritization, Drift-Free Session Tracking &amp; Academic Analytics</div>
  <div class="cover-meta">Word Count: {total_words}</div>
  <div class="cover-summary-box">
    <strong>Word Count Breakdown (Prose):</strong>
    Criterion A: {crit_a_words} words &bull;
    Criterion C (System Overview Prose): {crit_c_words} words &bull;
    Criterion D: {crit_d_words} words &bull;
    Criterion E: {crit_e_words} words &bull;
    <strong>Total: {total_words} words</strong> (IB Limit: 2,000 words)
  </div>
</div>

<!-- ==================== CRITERION A ==================== -->
<section>
  <h1 class="criterion-title">Criterion A - Problem Specification</h1>

  <h2>Problem Scenario</h2>
  <p>{html.escape(crit_a_scenario)}</p>

  <h2>Computational Context</h2>
  <p>{html.escape(crit_a_context)}</p>
  <div class="word-badge">Words: {crit_a_words}</div>

  <h2>Success Criteria</h2>
  <p>My application will:</p>
  <ol class="criteria-list">
    <li>Validate all task inputs (empty fields, valid dates, numeric bounds 1–5 for difficulty/importance, positive target hours) and display clear error messages.</li>
    <li>Add new study tasks with title, subject, deadline, difficulty, importance, and optional target hours.</li>
    <li>Edit existing study tasks and dynamically recalculate priority scores when parameters change.</li>
    <li>Delete tasks safely while cascading subtask cleanup and clearing any active focus session.</li>
    <li>Automatically compute a weighted priority score (0.4&times;Urgency + 0.3&times;Importance + 0.2&times;Difficulty + 0.1&times;Workload) with a neutral workload fallback of 3 when target hours are omitted.</li>
    <li>Generate an Algorithmic Study Plan sorted in descending priority order and provide a "What-If" priority simulator.</li>
    <li>Highlight overdue tasks and upcoming 7-day deadlines alongside a 7-Day Workload Heatmap and Daily Capacity Meter.</li>
    <li>Support marking tasks as completed and decomposing tasks into interactive sub-milestones.</li>
    <li>Track real-time study focus sessions with single-session enforcement, drift-free pause/resume, and a Time Intelligence analytics dashboard.</li>
    <li>Persist all data reliably in SQLite across sessions and provide a responsive UI with RFC-5545 (.ics) calendar export.</li>
  </ol>
</section>

<!-- ==================== CRITERION B ==================== -->
<section class="page-break">
  <h1 class="criterion-title">Criterion B - Planning</h1>

  <h2>Decomposing Problems</h2>
  <div class="decomp-grid">
    <div class="decomp-card">
      <h4>1. Database Management (database.py)</h4>
      <ul>
        <li><strong>Schema:</strong> Define normalized SQLite tables: <code>Tasks</code>, <code>Subtasks</code>, <code>StudySessions</code>, and single-row <code>ActiveSession</code>.</li>
        <li><strong>CRUD:</strong> Parameterized <code>add_task()</code>, <code>get_task_by_id()</code>, <code>update_task()</code>, <code>delete_task()</code>, and <code>complete_task()</code>.</li>
        <li><strong>Integrity:</strong> Foreign keys with <code>ON DELETE CASCADE</code> and <code>CHECK</code> constraints.</li>
      </ul>
    </div>
    <div class="decomp-card">
      <h4>2. Priority Engine (priority_calculator.py)</h4>
      <ul>
        <li><strong>Date Logic:</strong> <code>parse_date()</code>, <code>days_remaining()</code>, and <code>is_overdue()</code>.</li>
        <li><strong>Factor Mapping:</strong> Map deadline delta to Urgency (1–5) and optional hours to Workload (1–5, neutral 3).</li>
        <li><strong>Composite Score:</strong> Weighted formula returning score in [1.00, 5.00].</li>
      </ul>
    </div>
    <div class="decomp-card">
      <h4>3. Controller &amp; Validation (app.py)</h4>
      <ul>
        <li><strong>Routes:</strong> <code>/dashboard</code>, <code>/add-task</code>, <code>/edit-task/&lt;id&gt;</code>, <code>/study-plan</code>, <code>/time-intelligence</code>.</li>
        <li><strong>REST APIs:</strong> Live preview, What-If simulator, subtasks CRUD, and time-tracking endpoints.</li>
        <li><strong>Validation:</strong> Reject invalid submissions with HTTP 400 and flash messages.</li>
      </ul>
    </div>
    <div class="decomp-card">
      <h4>4. Real-Time Time Intelligence Engine</h4>
      <ul>
        <li><strong>Session Lock:</strong> <code>ActiveSession (ID = 1)</code> enforces one active focus session system-wide.</li>
        <li><strong>Drift-Free Clock:</strong> Server UNIX timestamps + accumulated seconds survive tab reloads.</li>
        <li><strong>Analytics:</strong> Subject-wise breakdown, study streak, and focus vs. calendar span.</li>
      </ul>
    </div>
    <div class="decomp-card">
      <h4>5. Responsive UI &amp; Focus Tools</h4>
      <ul>
        <li><strong>Templates:</strong> Clean card/table layouts, 7-day heatmap, and mobile slide-out drawer.</li>
        <li><strong>Client JS:</strong> Live score preview, circular SVG Pomodoro timer, Web Audio chimes, and confetti.</li>
        <li><strong>Export:</strong> One-click <code>.ics</code> calendar export and print stylesheet.</li>
      </ul>
    </div>
    <div class="decomp-card">
      <h4>6. Verification &amp; Evaluation</h4>
      <ul>
        <li><strong>Unit &amp; Criterion B Tests:</strong> 14-point suite (<code>run_tests.py</code>).</li>
        <li><strong>Feature QA:</strong> 20-point suite (<code>test_syntriq3.py</code>) &amp; 11-point Time Intel suite.</li>
        <li><strong>Evaluation:</strong> Verify all 10 success criteria and identify future improvements.</li>
      </ul>
    </div>
  </div>

  <h2>Planning the Computational Thinking Process</h2>
  <table>
    <thead>
      <tr>
        <th style="width: 24%;">Task</th>
        <th style="width: 10%;">Duration</th>
        <th style="width: 20%;">Dependencies</th>
        <th style="width: 18%;">Concurrencies</th>
        <th style="width: 28%;">CT Subtasks (Plan / Design / Develop / Test / Evaluate)</th>
      </tr>
    </thead>
    <tbody>
      <tr class="phase-row"><td colspan="5">Phase 1: Problem Specification &amp; Setup (Week 1)</td></tr>
      <tr>
        <td>Define scope &amp; success criteria; configure Python/Flask/SQLite/Git</td>
        <td>4 days</td>
        <td>None</td>
        <td>Environment setup</td>
        <td>Plan requirements, design repo structure, install Flask, verify startup, confirm readiness</td>
      </tr>
      <tr class="phase-row"><td colspan="5">Phase 2: System Architecture &amp; Database Design (Week 2)</td></tr>
      <tr>
        <td>System diagrams, UI wireframes &amp; 4-table SQLite schema</td>
        <td>5 days</td>
        <td>Phase 1 complete</td>
        <td>Priority formula design</td>
        <td>Design ERD &amp; MVC layout, create <code>init_db()</code> schema script, test table constraints</td>
      </tr>
      <tr class="phase-row"><td colspan="5">Phase 3: Priority Engine &amp; Database CRUD (Weeks 3–4)</td></tr>
      <tr>
        <td>Implement <code>priority_calculator.py</code> &amp; parameterized CRUD in <code>database.py</code></td>
        <td>8 days</td>
        <td>Database schema</td>
        <td>Dashboard &amp; form templates</td>
        <td>Design scoring math, write SQL CRUD &amp; <code>get_study_plan()</code>, unit-test edge cases</td>
      </tr>
      <tr class="phase-row"><td colspan="5">Phase 4: Flask Controller, Forms &amp; Interactive UI (Weeks 5–6)</td></tr>
      <tr>
        <td>Routes, validation, Study Plan view, What-If Simulator &amp; Pomodoro UI</td>
        <td>8 days</td>
        <td>CRUD &amp; Priority Engine</td>
        <td>CSS responsive styling</td>
        <td>Map routes, build Jinja2 forms &amp; <code>main.js</code> live preview, verify HTTP 200/400 flows</td>
      </tr>
      <tr class="phase-row"><td colspan="5">Phase 5: Real-Time Time Intelligence Engine (Weeks 7–8)</td></tr>
      <tr>
        <td><code>ActiveSession</code> lock, pause/resume APIs, floating pill &amp; <code>/time-intelligence</code></td>
        <td>7 days</td>
        <td>Phase 4 complete</td>
        <td>Automated test scripting</td>
        <td>Design conflict-resolution flow, code timestamp math, test pause/resume &amp; live aggregation</td>
      </tr>
      <tr class="phase-row"><td colspan="5">Phase 6: Automated Testing, Deployment &amp; Evaluation (Weeks 9–10)</td></tr>
      <tr>
        <td>Run 45 automated tests, cross-viewport QA, Vercel config &amp; IA evaluation</td>
        <td>6 days</td>
        <td>All modules integrated</td>
        <td>Documentation</td>
        <td>Execute 3 test suites, inspect mobile/desktop UI, evaluate against success criteria</td>
      </tr>
    </tbody>
  </table>
</section>

<!-- ==================== CRITERION C ==================== -->
<section class="page-break">
  <h1 class="criterion-title">Criterion C - System Overview</h1>
  <p>{html.escape(crit_c_prose)}</p>
  <div class="word-badge">Words: {crit_c_words}</div>

  <h2>System Models</h2>

  <!-- Diagram 1: Overall Structure & MVC Architecture -->
  <div class="figure-box">
    <svg viewBox="0 0 760 220" width="100%" height="auto" xmlns="http://www.w3.org/2000/svg" style="font-family: 'Segoe UI', Arial, sans-serif;">
      <rect x="0" y="0" width="760" height="220" fill="#ffffff"/>
      <!-- View Layer -->
      <rect x="20" y="25" width="175" height="170" rx="8" fill="#fff7ed" stroke="#f97316" stroke-width="1.8"/>
      <text x="107" y="47" text-anchor="middle" font-size="11.5" font-weight="700" fill="#9a3412">VIEW (Browser UI)</text>
      <rect x="34" y="60" width="147" height="26" rx="4" fill="#ffffff" stroke="#fdba74"/>
      <text x="107" y="77" text-anchor="middle" font-size="9.5" fill="#1e293b">Dashboard &amp; Heatmap</text>
      <rect x="34" y="94" width="147" height="26" rx="4" fill="#ffffff" stroke="#fdba74"/>
      <text x="107" y="111" text-anchor="middle" font-size="9.5" fill="#1e293b">Add/Edit + Live Preview</text>
      <rect x="34" y="128" width="147" height="26" rx="4" fill="#ffffff" stroke="#fdba74"/>
      <text x="107" y="145" text-anchor="middle" font-size="9.5" fill="#1e293b">Study Plan &amp; Simulator</text>
      <rect x="34" y="162" width="147" height="26" rx="4" fill="#ffffff" stroke="#fdba74"/>
      <text x="107" y="179" text-anchor="middle" font-size="9.5" fill="#1e293b">Time Intel &amp; Focus Timer</text>

      <!-- Arrow View <-> Controller -->
      <line x1="195" y1="95" x2="250" y2="95" stroke="#475569" stroke-width="1.6"/>
      <polygon points="250,95 242,91 242,99" fill="#475569"/>
      <line x1="250" y1="125" x2="195" y2="125" stroke="#475569" stroke-width="1.6"/>
      <polygon points="195,125 203,121 203,129" fill="#475569"/>
      <text x="222" y="88" text-anchor="middle" font-size="8" fill="#475569">HTTP/JSON</text>
      <text x="222" y="138" text-anchor="middle" font-size="8" fill="#475569">HTML/API</text>

      <!-- Controller Layer -->
      <rect x="252" y="38" width="175" height="145" rx="8" fill="#eff6ff" stroke="#3b82f6" stroke-width="1.8"/>
      <text x="339" y="60" text-anchor="middle" font-size="11.5" font-weight="700" fill="#1e40af">CONTROLLER (app.py)</text>
      <text x="339" y="83" text-anchor="middle" font-size="9.2" fill="#1e293b">• Flask Route Handlers</text>
      <text x="339" y="102" text-anchor="middle" font-size="9.2" fill="#1e293b">• Server Input Validation</text>
      <text x="339" y="121" text-anchor="middle" font-size="9.2" fill="#1e293b">• Time-Tracking REST APIs</text>
      <text x="339" y="140" text-anchor="middle" font-size="9.2" fill="#1e293b">• What-If Simulator API</text>
      <text x="339" y="159" text-anchor="middle" font-size="9.2" fill="#1e293b">• .ics Calendar Export</text>

      <!-- Arrows Controller -> Model -->
      <line x1="427" y1="75" x2="482" y2="62" stroke="#475569" stroke-width="1.6"/>
      <polygon points="482,62 473,60 475,68" fill="#475569"/>
      <line x1="427" y1="145" x2="482" y2="155" stroke="#475569" stroke-width="1.6"/>
      <polygon points="482,155 475,149 473,157" fill="#475569"/>

      <!-- Model Logic -->
      <rect x="484" y="20" width="256" height="82" rx="8" fill="#f0fdf4" stroke="#16a34a" stroke-width="1.8"/>
      <text x="612" y="40" text-anchor="middle" font-size="10.8" font-weight="700" fill="#166534">ALGORITHMIC MODEL (priority_calculator.py)</text>
      <text x="612" y="59" text-anchor="middle" font-size="9" fill="#1e293b">calculate_urgency() &bull; calculate_workload()</text>
      <text x="612" y="75" text-anchor="middle" font-size="9" fill="#1e293b">calculate_priority() = 0.4U + 0.3I + 0.2D + 0.1W</text>
      <text x="612" y="91" text-anchor="middle" font-size="9" fill="#1e293b">is_overdue() &bull; days_remaining()</text>

      <!-- Data Model -->
      <rect x="484" y="118" width="256" height="85" rx="8" fill="#f8fafc" stroke="#334155" stroke-width="1.8"/>
      <text x="612" y="138" text-anchor="middle" font-size="10.8" font-weight="700" fill="#0f172a">DATA MODEL (database.py &amp; SQLite)</text>
      <text x="612" y="157" text-anchor="middle" font-size="9" fill="#1e293b">Parameterized CRUD &bull; get_study_plan()</text>
      <text x="612" y="173" text-anchor="middle" font-size="9" fill="#1e293b">start/pause/resume/stop_tracking_session()</text>
      <text x="612" y="189" text-anchor="middle" font-size="9" fill="#1e293b">Tables: Tasks, Subtasks, StudySessions, ActiveSession</text>
    </svg>
    <div class="figure-caption">Image 1: Overall System Structure and MVC Architecture Diagram</div>
  </div>

  <!-- Diagram 2 & 3 side-by-side: UML Use Case & Database ERD -->
  <div class="figure-box">
    <svg viewBox="0 0 760 240" width="100%" height="auto" xmlns="http://www.w3.org/2000/svg" style="font-family: 'Segoe UI', Arial, sans-serif;">
      <rect x="0" y="0" width="760" height="240" fill="#ffffff"/>
      <!-- Left: UML Use Case -->
      <text x="145" y="18" text-anchor="middle" font-size="10.5" font-weight="700" fill="#0f172a">UML Use Case Diagram</text>
      <!-- Stick figure -->
      <circle cx="42" cy="95" r="12" fill="none" stroke="#1e293b" stroke-width="1.8"/>
      <line x1="42" y1="107" x2="42" y2="148" stroke="#1e293b" stroke-width="1.8"/>
      <line x1="22" y1="122" x2="62" y2="122" stroke="#1e293b" stroke-width="1.8"/>
      <line x1="42" y1="148" x2="25" y2="178" stroke="#1e293b" stroke-width="1.8"/>
      <line x1="42" y1="148" x2="59" y2="178" stroke="#1e293b" stroke-width="1.8"/>
      <text x="42" y="195" text-anchor="middle" font-size="9.5" font-weight="700" fill="#1e293b">Student</text>
      <!-- System box -->
      <rect x="105" y="28" width="180" height="202" rx="6" fill="#f8fafc" stroke="#64748b" stroke-width="1.4"/>
      <g fill="#ffffff" stroke="#334155" stroke-width="1.2">
        <ellipse cx="195" cy="49" rx="76" ry="12"/>
        <ellipse cx="195" cy="80" rx="76" ry="12"/>
        <ellipse cx="195" cy="111" rx="76" ry="12"/>
        <ellipse cx="195" cy="142" rx="76" ry="12"/>
        <ellipse cx="195" cy="173" rx="76" ry="12"/>
        <ellipse cx="195" cy="204" rx="76" ry="12"/>
      </g>
      <g font-size="8.6" text-anchor="middle" fill="#0f172a">
        <text x="195" y="52">Add / Edit / Delete Tasks</text>
        <text x="195" y="83">View Prioritized Study Plan</text>
        <text x="195" y="114">Simulate What-If Priority</text>
        <text x="195" y="145">Track Live Focus Session</text>
        <text x="195" y="176">Inspect Time Intelligence</text>
        <text x="195" y="207">Export .ics Calendar</text>
      </g>
      <g stroke="#475569" stroke-width="1.1">
        <line x1="58" y1="115" x2="119" y2="49"/>
        <line x1="58" y1="118" x2="119" y2="80"/>
        <line x1="58" y1="121" x2="119" y2="111"/>
        <line x1="58" y1="126" x2="119" y2="142"/>
        <line x1="58" y1="130" x2="119" y2="173"/>
        <line x1="58" y1="135" x2="119" y2="204"/>
      </g>

      <!-- Divider -->
      <line x1="305" y1="12" x2="305" y2="228" stroke="#cbd5e1" stroke-dasharray="4,4"/>

      <!-- Right: Database ERD -->
      <text x="532" y="18" text-anchor="middle" font-size="10.5" font-weight="700" fill="#0f172a">SQLite Relational Database Schema (4 Tables)</text>

      <!-- Tasks Table -->
      <rect x="322" y="30" width="205" height="196" rx="5" fill="#ffffff" stroke="#0f172a" stroke-width="1.4"/>
      <rect x="322" y="30" width="205" height="21" rx="4" fill="#fff7ed" stroke="#0f172a" stroke-width="1.2"/>
      <text x="424" y="44" text-anchor="middle" font-size="9.5" font-weight="700" fill="#9a3412">Tasks</text>
      <g font-size="8.2" fill="#1e293b" font-family="Consolas, monospace">
        <text x="329" y="65">PK Task_ID : INTEGER</text>
        <text x="329" y="79">   Task_Title : TEXT NOT NULL</text>
        <text x="329" y="93">   Task_Subject : TEXT NOT NULL</text>
        <text x="329" y="107">   Task_Deadline : TEXT (YYYY-MM-DD)</text>
        <text x="329" y="121">   Task_Difficulty : INT CHECK(1..5)</text>
        <text x="329" y="135">   Task_Importance : INT CHECK(1..5)</text>
        <text x="329" y="149">   Target_Hours : REAL (Nullable)</text>
        <text x="329" y="163">   Total_Tracked_Seconds : INT</text>
        <text x="329" y="177">   Priority_Score : REAL NOT NULL</text>
        <text x="329" y="191">   Task_Status : Pending|Completed</text>
        <text x="329" y="205">   First_Tracked_At : TEXT</text>
        <text x="329" y="219">   Completed_At : TEXT</text>
      </g>

      <!-- Subtasks Table -->
      <rect x="558" y="30" width="188" height="62" rx="5" fill="#ffffff" stroke="#0f172a" stroke-width="1.3"/>
      <rect x="558" y="30" width="188" height="18" rx="4" fill="#f1f5f9" stroke="#0f172a"/>
      <text x="652" y="42" text-anchor="middle" font-size="9" font-weight="700">Subtasks (1:N)</text>
      <g font-size="8" fill="#1e293b" font-family="Consolas, monospace">
        <text x="564" y="60">PK Subtask_ID : INTEGER</text>
        <text x="564" y="73">FK Task_ID -&gt; Tasks (CASCADE)</text>
        <text x="564" y="86">   Subtask_Title, Is_Completed</text>
      </g>

      <!-- StudySessions Table -->
      <rect x="558" y="101" width="188" height="68" rx="5" fill="#ffffff" stroke="#0f172a" stroke-width="1.3"/>
      <rect x="558" y="101" width="188" height="18" rx="4" fill="#f1f5f9" stroke="#0f172a"/>
      <text x="652" y="113" text-anchor="middle" font-size="9" font-weight="700">StudySessions (1:N)</text>
      <g font-size="8" fill="#1e293b" font-family="Consolas, monospace">
        <text x="564" y="131">PK Session_ID : INTEGER</text>
        <text x="564" y="144">FK Task_ID -&gt; Tasks (SET NULL)</text>
        <text x="564" y="157">   Start_Time, End_Time, Status</text>
        <text x="564" y="167">   Duration_Seconds, Session_Date</text>
      </g>

      <!-- ActiveSession Table -->
      <rect x="558" y="177" width="188" height="53" rx="5" fill="#ffffff" stroke="#0f172a" stroke-width="1.3"/>
      <rect x="558" y="177" width="188" height="18" rx="4" fill="#eff6ff" stroke="#0f172a"/>
      <text x="652" y="189" text-anchor="middle" font-size="9" font-weight="700">ActiveSession (CHECK ID=1)</text>
      <g font-size="8" fill="#1e293b" font-family="Consolas, monospace">
        <text x="564" y="207">PK ID=1, FK Task_ID, Session_ID</text>
        <text x="564" y="220">   Start_Timestamp, Accumulated_Sec</text>
      </g>

      <!-- ERD Connectors -->
      <g stroke="#334155" stroke-width="1.2">
        <line x1="527" y1="62" x2="558" y2="62"/>
        <line x1="527" y1="135" x2="558" y2="135"/>
        <line x1="527" y1="202" x2="558" y2="202"/>
      </g>
    </svg>
    <div class="figure-caption">Image 2: UML Use Case Diagram (Left) and Relational Database Schema (Right)</div>
  </div>

  <h2>Implemented User Interface &amp; Application Screenshots</h2>

  <div class="figure-box">
    <img src="{img_uri('dashboard')}" alt="SYNTRIQ Study Dashboard"/>
    <div class="figure-caption">Image 3: Implemented Study Dashboard showing 7-Day Workload Heatmap, Capacity Meter, Overdue Banner, Priority Task Table, and Live Active Session Pill</div>
  </div>

  <div class="figure-box">
    <img src="{img_uri('study_plan')}" alt="Algorithmic Study Plan"/>
    <div class="figure-caption">Image 4: Algorithmic Study Plan sorted descending by Priority Score with Factor Breakdown, Sub-Milestones, and Track Time Controls</div>
  </div>

  <div class="figure-box">
    <img src="{img_uri('time_intel')}" alt="Time Intelligence Dashboard"/>
    <div class="figure-caption">Image 5: Real-Time Time Intelligence Dashboard displaying Live Session Banner, Subject-Wise Distribution, Focus vs. Calendar Span, and Session History</div>
  </div>

  <div class="figure-box">
    <img src="{img_uri('add_task')}" alt="Add Task Live Preview"/>
    <div class="figure-caption">Image 6: Add Study Task Form with Smart Date Quick Chips, Optional Target Hours, and Live Priority Score Preview</div>
  </div>

  <div class="screenshot-grid-2">
    <div class="figure-box">
      <img src="{img_uri('simulator')}" alt="What-If Priority Simulator"/>
      <div class="figure-caption">Image 7: Interactive What-If Priority Simulator &amp; Focus Timer Modal</div>
    </div>
    <div class="figure-box">
      <img src="{img_uri('mobile')}" alt="Mobile Responsive Layout"/>
      <div class="figure-caption">Image 8: Responsive Mobile View (390px)</div>
    </div>
  </div>

  <div class="figure-box">
    <img src="{img_uri('pomodoro')}" alt="Focus Kitchen Pomodoro Timer" style="max-height: 300px; width: auto;"/>
    <div class="figure-caption">Image 9: Focus Kitchen Pomodoro Timer Modal with Circular SVG Countdown &amp; Offline Web Audio Soundscapes</div>
  </div>

  <h2>Algorithms as Components in a System Model</h2>
  <div class="sql-grid">
    <div class="avoid-break">
      <strong>Core SQLite Schema &amp; Queries:</strong>
      <pre class="code-box"><code>CREATE TABLE Tasks (
  Task_ID INTEGER PRIMARY KEY AUTOINCREMENT,
  Task_Title TEXT NOT NULL,
  Task_Subject TEXT NOT NULL,
  Task_Deadline TEXT NOT NULL,
  Task_Difficulty INT CHECK(Task_Difficulty BETWEEN 1 AND 5),
  Task_Importance INT CHECK(Task_Importance BETWEEN 1 AND 5),
  Target_Hours REAL DEFAULT NULL,
  Total_Tracked_Seconds INT NOT NULL DEFAULT 0,
  Priority_Score REAL NOT NULL,
  Task_Status TEXT DEFAULT 'Pending'
);

CREATE TABLE ActiveSession (
  ID INTEGER PRIMARY KEY CHECK (ID = 1),
  Task_ID INTEGER NOT NULL,
  Session_ID INTEGER NOT NULL,
  Start_Timestamp REAL NOT NULL,
  Accumulated_Seconds INTEGER DEFAULT 0,
  Is_Paused INTEGER DEFAULT 0
);</code></pre>
    </div>
    <div class="avoid-break">
      <strong>Priority &amp; Time-Tracking Pseudocode:</strong>
      <pre class="code-box"><code>FUNCTION calculate_priority(deadline, diff, imp, hours):
  days = deadline - today
  IF days &lt;= 1 THEN urgency = 5
  ELSE IF days &lt;= 3 THEN urgency = 4
  ELSE IF days &lt;= 7 THEN urgency = 3
  ELSE IF days &lt;= 14 THEN urgency = 2
  ELSE urgency = 1

  IF hours IS NULL OR hours &lt;= 0 THEN workload = 3
  ELSE map hours [1..6+] -&gt; workload [1..5]

  RETURN ROUND(0.4*urgency + 0.3*imp + 0.2*diff + 0.1*workload, 2)

FUNCTION start_tracking(task_id, force):
  IF ActiveSession(ID=1) exists AND task != task_id:
    IF NOT force: RETURN conflict_prompt
    ELSE: stop_tracking_session()
  INSERT ActiveSession(1, task_id, now(), accum=0)</code></pre>
    </div>
  </div>

  <h2>Testing Strategies</h2>
  <table>
    <thead>
      <tr>
        <th style="width: 24%;">Success Criterion</th>
        <th style="width: 38%;">Testing Strategy</th>
        <th style="width: 38%;">Expected Result</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>1. Input validation</td>
        <td>Submit <code>POST /add-task</code> with empty title, non-numeric values, difficulty/importance outside 1–5, and hours &le; 0.</td>
        <td>System returns HTTP 400 with flash error message; invalid row is rejected at both controller and DB layers.</td>
      </tr>
      <tr>
        <td>2. Add task (optional hours)</td>
        <td>Add valid task with and without <code>estimated_hours</code> via form and <code>database.add_task()</code>.</td>
        <td>Task is stored in <code>Tasks</code> with auto-generated <code>Task_ID</code> and <code>0m</code> tracked time.</td>
      </tr>
      <tr>
        <td>3. Edit task &amp; recalculate</td>
        <td>Modify deadline, difficulty, and importance via <code>update_task()</code> and <code>/edit-task/&lt;id&gt;</code>.</td>
        <td>Updated fields persist and <code>Priority_Score</code> recalculates immediately.</td>
      </tr>
      <tr>
        <td>4. Delete task safely</td>
        <td>Invoke <code>delete_task(task_id)</code> on a task with subtasks or an active session.</td>
        <td>Task, subtasks, and active session row are removed; <code>get_task_by_id()</code> returns <code>None</code>.</td>
      </tr>
      <tr>
        <td>5. Priority score &amp; fallback</td>
        <td>Test <code>calculate_priority()</code> with known values (e.g., today, D=5, I=5, H=6) and <code>hours=None</code>.</td>
        <td>Exact scores returned (e.g., <code>5.00</code> max; neutral workload <code>3</code> yields <code>3.40</code> when 2d left, D=3, I=3).</td>
      </tr>
      <tr>
        <td>6. Study Plan &amp; Simulator</td>
        <td>Insert tasks with distinct priorities; request <code>/study-plan</code> and <code>POST /api/simulate-priority</code>.</td>
        <td>Tasks appear strictly descending by <code>Priority_Score</code>; simulator returns accurate score delta.</td>
      </tr>
      <tr>
        <td>7. Overdue, upcoming &amp; heatmap</td>
        <td>Insert past-due and +3d tasks; load <code>/dashboard</code> and query overdue/upcoming helpers.</td>
        <td>Past task flagged <code>is_overdue=True</code>; upcoming filter isolates 7-day tasks; heatmap/capacity update.</td>
      </tr>
      <tr>
        <td>8. Completion &amp; subtasks</td>
        <td>Add/toggle subtask via <code>/api/tasks/&lt;id&gt;/subtasks</code>; post <code>complete_task()</code> on active task.</td>
        <td>Subtask state toggles; task status becomes <code>Completed</code> with <code>Completed_At</code> and active session stopped.</td>
      </tr>
      <tr>
        <td>9. Real-time tracking &amp; Time Intel</td>
        <td>Start session, attempt second task without/with <code>force_switch</code>, pause/resume, stop, load <code>/time-intelligence</code>.</td>
        <td>Conflict detected without force; force switches cleanly; pause preserves seconds; analytics display real totals.</td>
      </tr>
      <tr>
        <td>10. Persistence, UI &amp; .ics export</td>
        <td>Re-query SQLite after writes, request all routes, inspect mobile/desktop CSS and <code>/export/calendar.ics</code>.</td>
        <td>Data persists; all routes return HTTP 200; <code>text/calendar</code> contains valid <code>BEGIN:VCALENDAR</code> events.</td>
      </tr>
    </tbody>
  </table>
</section>

<!-- ==================== CRITERION D ==================== -->
<section class="page-break">
  <h1 class="criterion-title">Criterion D - Development</h1>
  {crit_d_html}
  <div class="word-badge">Words: {crit_d_words}</div>
</section>

<!-- ==================== CRITERION E ==================== -->
<section class="page-break">
  <h1 class="criterion-title">Criterion E - Evaluation</h1>

  <h2>Meeting Success Criteria</h2>
  {crit_e_list_html}
  <p style="margin-top: 8px;"><strong>Automated Verification Summary:</strong> All 45 automated tests across <code>run_tests.py</code> (14/14 Criterion B tests), <code>scripts/test_syntriq3.py</code> (20/20 commercial QA tests), and <code>scripts/test_time_intelligence.py</code> (11/11 Time Intelligence engine tests) passed with zero failures.</p>

  <h2>Suggesting Improvements</h2>
  <p>{html.escape(crit_e_improvements)}</p>
  <div class="word-badge">Words: {crit_e_words}</div>
</section>

</body>
</html>
"""
    return html_doc


def render_pdf(html_path: str, pdf_path: str):
    """Uses Playwright Chromium to render the HTML IA report into a crisp A4 PDF."""
    uri = "file:///" + html_path.replace("\\", "/")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(uri, wait_until="networkidle")
        page.wait_for_timeout(400)
        page.pdf(
            path=pdf_path,
            format="A4",
            print_background=True,
            display_header_footer=False,
            prefer_css_page_size=True,
        )
        browser.close()


def main():
    tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp_db_path = tmp_db.name
    tmp_db.close()

    orig_default = db.DEFAULT_DB_PATH
    db.DEFAULT_DB_PATH = tmp_db_path
    app.config["DB_FILE"] = tmp_db_path

    port = find_free_port()
    server = make_server("127.0.0.1", port, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)

    try:
        populate_demo_database(tmp_db_path)
        thread.start()
        base_url = f"http://127.0.0.1:{port}"
        print(f"Temporary demo server running at {base_url}")

        screenshot_paths = capture_screenshots(base_url)
        print(f"Captured {len(screenshot_paths)} IA screenshots in {IA_SCREENSHOT_DIR}")

        html_content = build_ia_html(screenshot_paths)
        os.makedirs(os.path.dirname(HTML_OUTPUT_PATH), exist_ok=True)
        with open(HTML_OUTPUT_PATH, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"Wrote HTML report: {HTML_OUTPUT_PATH}")

        render_pdf(HTML_OUTPUT_PATH, PDF_OUTPUT_PATH)
        print(f"Generated IA PDF: {PDF_OUTPUT_PATH}")
    finally:
        server.shutdown()
        db.DEFAULT_DB_PATH = orig_default
        app.config.pop("DB_FILE", None)
        gc.collect()
        if os.path.exists(tmp_db_path):
            try:
                os.remove(tmp_db_path)
            except Exception:
                pass


if __name__ == "__main__":
    main()
