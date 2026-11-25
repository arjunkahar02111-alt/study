"""
Smart Study Planner (SYNTRIQ) - Flask Web Application
Implements Multi-User Firebase Authentication, Google Sign-In,
Cloud Firestore UID Data Isolation, Priority Scheduling & Real-Time Time Intelligence.
"""

import os
import random
from datetime import date, datetime, timedelta, timezone
from functools import wraps

from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix
from flask import (
    Flask,
    Response,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

import database
import firebase_auth
import firestore_store
import store
from priority_calculator import calculate_priority, is_overdue, parse_date

load_dotenv()

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.secret_key = os.environ.get("SECRET_KEY", "smart-study-planner-secret-key-2026")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(os.environ.get("VERCEL")),
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
)

# Database path (SQLite used for local/offline mode and legacy migration checks)
if os.environ.get("VERCEL"):
    import shutil
    import tempfile

    DB_FILE = os.path.join(tempfile.gettempdir(), "study_planner.db")
    orig_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "study_planner.db")
    if not os.path.exists(DB_FILE) and os.path.exists(orig_db):
        try:
            shutil.copy2(orig_db, DB_FILE)
        except Exception:
            pass
else:
    DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "study_planner.db")


def get_db():
    """Returns the active SQLite database file path, allowing dynamic testing overrides."""
    return app.config.get("DB_FILE", DB_FILE)


MOTIVATIONAL_QUOTES = [
    {"quote": "It always seems impossible until it's done.", "author": "Nelson Mandela"},
    {"quote": "Live as if you were to die tomorrow. Learn as if you were to live forever.", "author": "Mahatma Gandhi"},
    {"quote": "Success is the sum of small efforts, repeated day in and day out.", "author": "Robert Collier"},
    {"quote": "The expert in anything was once a beginner.", "author": "Helen Hayes"},
    {"quote": "Don't watch the clock; do what it does. Keep going.", "author": "Sam Levenson"},
    {"quote": "Nothing in life is to be feared, it is only to be understood.", "author": "Marie Curie"},
    {"quote": "You don't have to be great to start, but you have to start to be great.", "author": "Zig Ziglar"},
]


def setup_application():
    """Initializes local SQLite schema without forcing seed tasks."""
    try:
        database.init_db(DB_FILE)
    except Exception:
        # Gracefully defer if default DB_FILE is on a read-only filesystem or overridden by tests
        pass


setup_application()


def get_current_user():
    """Returns the authenticated user dictionary from Flask session if valid, else None."""
    user = session.get("user")
    if not user or not isinstance(user, dict) or not user.get("uid"):
        return None
    return user


def login_required(f):
    """Protects routes and APIs, rejecting unauthenticated access cleanly."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required", "auth_required": True}), 401
            next_url = request.full_path.rstrip("?")
            return redirect(url_for("login_page", next=next_url))
        g.user = user
        return f(*args, **kwargs)

    return decorated


@app.errorhandler(firestore_store.FirestorePermissionError)
def handle_firestore_permission_error(err):
    """Handles expired tokens or unauthorized Firestore access cleanly."""
    if request.path.startswith("/api/"):
        return jsonify({"error": "Permission denied or session expired", "auth_required": True}), 403
    session.pop("user", None)
    flash("Your session expired or access was denied. Please sign in again.", "warning")
    return redirect(url_for("login_page"))


@app.context_processor
def inject_globals():
    """Injects current date, authenticated user, Firebase web config, and active session into Jinja templates."""
    today = date.today()
    user = get_current_user()
    active_session = None
    user_settings = {"maxSafeHours": 6.0, "defaultFocusMinutes": 25, "soundEffectsEnabled": True}
    if user:
        try:
            active_session = store.get_active_session(user, get_db())
        except Exception:
            active_session = None
        try:
            user_settings = store.get_user_settings(user, get_db())
        except Exception:
            pass
    return {
        "current_date": today,
        "active_session": active_session,
        "current_user": user,
        "user_settings": user_settings,
        "firebase_config": firebase_auth.get_firebase_web_config(),
        "firebase_enabled": firebase_auth.is_firebase_configured(),
    }


# =============================================================================
# Authentication & Session Management Routes
# =============================================================================

@app.route("/login")
def login_page():
    """Renders the SYNTRIQ Google Sign-In authentication screen."""
    if get_current_user():
        return redirect(url_for("dashboard"))
    next_url = request.args.get("next", "/dashboard")
    if not next_url.startswith("/"):
        next_url = "/dashboard"
    return render_template("login.html", next_url=next_url)


@app.route("/auth/session", methods=["POST"])
def auth_create_session():
    """
    Verifies a Firebase ID token submitted after Google Sign-In,
    initializes the user's personal workspace if first login,
    and establishes an HttpOnly server session.
    """
    data = request.get_json(silent=True) or {}
    id_token = (data.get("idToken") or "").strip()
    if not id_token:
        return jsonify({"error": "Missing Firebase ID token"}), 400

    try:
        claims = firebase_auth.verify_firebase_id_token(id_token)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 401

    user_obj = {
        "uid": claims["uid"],
        "email": claims["email"],
        "name": claims["name"],
        "picture": claims["picture"],
        "id_token": id_token,
    }

    try:
        is_new_user = store.ensure_user_workspace(user_obj, get_db())
    except firestore_store.FirestorePermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception as exc:
        return jsonify({"error": f"Failed to initialize workspace: {exc}"}), 500

    session.clear()
    session.permanent = True
    session["user"] = user_obj

    if is_new_user:
        first_name = (claims["name"] or "there").split()[0]
        flash(f"Welcome to SYNTRIQ, {first_name}! Your private study workspace is ready.", "success")

    return jsonify({
        "success": True,
        "is_new_user": is_new_user,
        "user": {
            "uid": claims["uid"],
            "email": claims["email"],
            "name": claims["name"],
            "picture": claims["picture"],
        },
    })


@app.route("/auth/refresh-token", methods=["POST"])
def auth_refresh_token():
    """Updates the verified Firebase ID token in the current session without interrupting UI."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    data = request.get_json(silent=True) or {}
    id_token = (data.get("idToken") or "").strip()
    if not id_token:
        return jsonify({"error": "Missing ID token"}), 400
    try:
        claims = firebase_auth.verify_firebase_id_token(id_token)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 401

    if claims["uid"] != user["uid"]:
        return jsonify({"error": "UID mismatch during token refresh"}), 403

    user["id_token"] = id_token
    user["email"] = claims["email"]
    user["name"] = claims["name"]
    user["picture"] = claims["picture"]
    session["user"] = user
    return jsonify({"success": True})


@app.route("/auth/logout", methods=["POST"])
def auth_logout():
    """
    Clears server-side session while safely preserving the user's
    saved study routines, tasks, and active timer state under their UID.
    """
    session.clear()
    if request.is_json:
        return jsonify({"success": True})
    flash("You have been signed out securely.", "info")
    return redirect(url_for("login_page"))


@app.route("/auth/me")
@login_required
def auth_me():
    user = g.user
    return jsonify({
        "authenticated": True,
        "uid": user["uid"],
        "email": user.get("email", ""),
        "name": user.get("name", ""),
        "picture": user.get("picture", ""),
    })


# =============================================================================
# Core Planner Routes (Protected & UID-Isolated)
# =============================================================================

@app.route("/")
@app.route("/dashboard")
@login_required
def dashboard():
    """User-isolated Study Dashboard."""
    filter_type = request.args.get("filter", "all").lower()
    user = g.user
    db_target = get_db()

    all_tasks = store.get_all_tasks(user, db_target)
    pending_tasks = [t for t in all_tasks if t["Task_Status"] == "Pending"]
    completed_tasks = [t for t in all_tasks if t["Task_Status"] == "Completed"]
    today_str = date.today().strftime("%Y-%m-%d")
    max_str = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")
    overdue_tasks = [t for t in pending_tasks if t["Task_Deadline"] < today_str]
    upcoming_tasks = [t for t in pending_tasks if today_str <= t["Task_Deadline"] <= max_str]

    if filter_type == "pending":
        display_tasks = pending_tasks
        active_tab_title = "Pending Tasks"
    elif filter_type == "completed":
        display_tasks = completed_tasks
        active_tab_title = "Completed Tasks"
    elif filter_type == "overdue":
        display_tasks = overdue_tasks
        active_tab_title = "Overdue Tasks"
    elif filter_type == "upcoming":
        display_tasks = upcoming_tasks
        active_tab_title = "Upcoming Deadlines (Next 7 Days)"
    else:
        filter_type = "all"
        display_tasks = all_tasks
        active_tab_title = "All Tasks"

    stats = {
        "total": len(all_tasks),
        "pending": len(pending_tasks),
        "completed": len(completed_tasks),
        "overdue": len(overdue_tasks),
        "upcoming": len(upcoming_tasks),
    }

    settings = store.get_user_settings(user, db_target)
    streak = store.get_study_streak(user, db_target)
    capacity = store.get_daily_capacity(user, db_target, max_safe_hours=float(settings.get("maxSafeHours", 6.0)))
    heatmap = store.get_weekly_workload_heatmap(user, db_target)
    routines = store.get_routines(user, db_target)
    legacy_migration = database.get_legacy_migration_status(db_target)
    quote = random.choice(MOTIVATIONAL_QUOTES)

    return render_template(
        "dashboard.html",
        tasks=display_tasks,
        stats=stats,
        filter_type=filter_type,
        active_tab_title=active_tab_title,
        overdue_tasks=overdue_tasks,
        upcoming_tasks=upcoming_tasks,
        streak=streak,
        capacity=capacity,
        heatmap=heatmap,
        routines=routines,
        legacy_migration=legacy_migration,
        quote=quote,
    )


@app.route("/add-task", methods=["GET", "POST"])
@login_required
def add_task():
    """Add Task Page scoped strictly to the authenticated user."""
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        subject = request.form.get("subject", "").strip()
        deadline = request.form.get("deadline", "").strip()
        difficulty = request.form.get("difficulty", "").strip()
        importance = request.form.get("importance", "").strip()
        estimated_hours = request.form.get("estimated_hours", "").strip()

        if not title or not subject or not deadline:
            flash("Please complete all required fields", "danger")
            return render_template("add_task.html", form_data=request.form), 400

        try:
            diff_int = int(difficulty)
            imp_int = int(importance)
            hours_float = float(estimated_hours) if estimated_hours else None
        except (ValueError, TypeError):
            flash("Invalid input", "danger")
            return render_template("add_task.html", form_data=request.form), 400

        if diff_int < 1 or diff_int > 5 or imp_int < 1 or imp_int > 5 or (hours_float is not None and hours_float <= 0):
            flash("Invalid input", "danger")
            return render_template("add_task.html", form_data=request.form), 400

        try:
            parse_date(deadline)
        except Exception:
            flash("Invalid deadline format. Please select a valid date.", "danger")
            return render_template("add_task.html", form_data=request.form), 400

        try:
            store.add_task(
                user=g.user,
                db_path=get_db(),
                title=title,
                subject=subject,
                deadline=deadline,
                difficulty=diff_int,
                importance=imp_int,
                estimated_hours=hours_float,
            )
            flash("Task added successfully", "success")
            return redirect(url_for("study_plan"))
        except Exception as e:
            flash(f"Error adding task: {str(e)}", "danger")
            return render_template("add_task.html", form_data=request.form), 500

    return render_template("add_task.html", form_data={})


@app.route("/study-plan")
@login_required
def study_plan():
    """Algorithmic Study Plan scoped strictly to the authenticated user."""
    tasks = store.get_study_plan(g.user, get_db())
    completed_tasks = store.get_completed_tasks(g.user, get_db())
    return render_template(
        "study_plan.html",
        tasks=tasks,
        completed_tasks=completed_tasks,
    )


@app.route("/edit-task/<task_id>", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    """Edit Task Page enforcing ownership via user UID."""
    task = store.get_task_by_id(g.user, get_db(), task_id)
    if not task:
        flash("Task not found", "danger")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        subject = request.form.get("subject", "").strip()
        deadline = request.form.get("deadline", "").strip()
        difficulty = request.form.get("difficulty", "").strip()
        importance = request.form.get("importance", "").strip()
        estimated_hours = request.form.get("estimated_hours", "").strip()
        status = request.form.get("status", task["Task_Status"]).strip()

        if not title or not subject or not deadline:
            flash("Please complete all required fields", "danger")
            return render_template("edit_task.html", task=task, form_data=request.form), 400

        try:
            diff_int = int(difficulty)
            imp_int = int(importance)
            hours_float = float(estimated_hours) if estimated_hours else None
        except (ValueError, TypeError):
            flash("Invalid input", "danger")
            return render_template("edit_task.html", task=task, form_data=request.form), 400

        if diff_int < 1 or diff_int > 5 or imp_int < 1 or imp_int > 5 or (hours_float is not None and hours_float <= 0):
            flash("Invalid input", "danger")
            return render_template("edit_task.html", task=task, form_data=request.form), 400

        try:
            parse_date(deadline)
        except Exception:
            flash("Invalid deadline date", "danger")
            return render_template("edit_task.html", task=task, form_data=request.form), 400

        try:
            store.update_task(
                user=g.user,
                db_path=get_db(),
                task_id=task_id,
                title=title,
                subject=subject,
                deadline=deadline,
                difficulty=diff_int,
                importance=imp_int,
                estimated_hours=hours_float,
                status=status,
            )
            flash("Task updated successfully", "success")
            return redirect(url_for("study_plan"))
        except Exception as e:
            flash(f"Error updating task: {str(e)}", "danger")
            return render_template("edit_task.html", task=task, form_data=request.form), 500

    return render_template("edit_task.html", task=task, form_data=task)


@app.route("/complete-task/<task_id>", methods=["POST"])
@login_required
def complete_task(task_id):
    """Marks a user's task as completed."""
    success = store.complete_task(g.user, get_db(), task_id)
    if success:
        flash("Task marked as completed", "success")
    else:
        flash("Task not found", "danger")

    redirect_to = request.referrer or url_for("study_plan")
    return redirect(redirect_to)


@app.route("/delete-task/<task_id>", methods=["POST"])
@login_required
def delete_task(task_id):
    """Deletes a user's task."""
    success = store.delete_task(g.user, get_db(), task_id)
    if success:
        flash("Task deleted successfully", "success")
    else:
        flash("Task not found", "danger")

    redirect_to = request.referrer or url_for("dashboard")
    return redirect(redirect_to)


# =============================================================================
# Personal Study Routines & Account Settings Routes
# =============================================================================

@app.route("/routines")
@login_required
def routines_page():
    """Displays the authenticated user's personal weekly study routine schedule."""
    selected_day = request.args.get("day", "All").strip()
    all_routines = store.get_routines(g.user, get_db())
    if selected_day != "All":
        filtered = [r for r in all_routines if r["dayOfWeek"].lower() == selected_day.lower()]
    else:
        filtered = all_routines
    return render_template(
        "routines.html",
        routines=filtered,
        all_routines_count=len(all_routines),
        selected_day=selected_day,
    )


@app.route("/routines/add", methods=["POST"])
@login_required
def add_routine_route():
    title = request.form.get("title", "").strip()
    subject = request.form.get("subject", "").strip()
    day_of_week = request.form.get("day_of_week", "").strip()
    start_time = request.form.get("start_time", "17:00").strip()
    end_time = request.form.get("end_time", "18:00").strip()
    focus_goal = request.form.get("focus_goal", "").strip()

    try:
        store.add_routine(
            user=g.user,
            db_path=get_db(),
            title=title,
            subject=subject,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            focus_goal=focus_goal,
        )
        flash("Study routine block added to your personal schedule.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("routines_page"))


@app.route("/routines/<routine_id>/toggle", methods=["POST"])
@login_required
def toggle_routine_route(routine_id):
    if store.toggle_routine(g.user, get_db(), routine_id):
        flash("Routine status updated.", "info")
    else:
        flash("Routine not found.", "danger")
    return redirect(request.referrer or url_for("routines_page"))


@app.route("/routines/<routine_id>/delete", methods=["POST"])
@login_required
def delete_routine_route(routine_id):
    if store.delete_routine(g.user, get_db(), routine_id):
        flash("Routine block removed.", "success")
    else:
        flash("Routine not found.", "danger")
    return redirect(request.referrer or url_for("routines_page"))


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings_page():
    """Account profile, preferences, and legacy local data migration settings."""
    if request.method == "POST":
        try:
            max_safe = float(request.form.get("max_safe_hours", 6.0))
            default_focus = int(request.form.get("default_focus_minutes", 25))
            sound_on = request.form.get("sound_effects_enabled") == "on"
            store.update_user_settings(g.user, get_db(), max_safe, default_focus, sound_on)
            flash("Your personal study preferences have been saved.", "success")
        except Exception as exc:
            flash(f"Could not save preferences: {exc}", "danger")
        return redirect(url_for("settings_page"))

    settings = store.get_user_settings(g.user, get_db())
    legacy_migration = database.get_legacy_migration_status(get_db())
    return render_template("settings.html", settings=settings, legacy_migration=legacy_migration)


@app.route("/api/migrate-legacy-data", methods=["POST"])
@login_required
def migrate_legacy_data():
    """Associates unclaimed pre-authentication SQLite data with the confirming user only."""
    try:
        count = database.migrate_legacy_data_to_user(
            uid=g.user["uid"],
            id_token=g.user.get("id_token") if firebase_auth.is_firebase_configured() else None,
            db_path=get_db(),
        )
        flash(f"Imported {count} pre-existing study task(s) into your private workspace.", "success")
        return jsonify({"success": True, "migrated_count": count})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/dismiss-legacy-migration", methods=["POST"])
@login_required
def dismiss_legacy_migration_api():
    database.dismiss_legacy_migration(get_db())
    return jsonify({"success": True})


# =============================================================================
# Priority Preview, Simulator, Export, Subtasks & Time Intelligence APIs
# =============================================================================

@app.route("/api/preview-priority", methods=["POST"])
@login_required
def preview_priority():
    data = request.get_json(silent=True) or request.form
    try:
        deadline = data.get("deadline")
        difficulty = int(data.get("difficulty", 3))
        importance = int(data.get("importance", 3))
        raw_hours = data.get("estimated_hours")
        hours_val = float(raw_hours) if raw_hours and str(raw_hours).strip() and float(raw_hours) > 0 else None

        score = calculate_priority(deadline, difficulty, importance, hours_val)
        overdue = is_overdue(deadline)
        return jsonify({"priority_score": score, "is_overdue": overdue})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/export/calendar.ics")
@login_required
def export_calendar():
    """Exports the authenticated user's pending tasks as an RFC-5545 iCalendar (.ics) file."""
    tasks = store.get_pending_tasks(g.user, get_db())

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Smart Study Planner//Priority Task Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:SYNTRIQ Study Planner Schedule",
    ]
    now_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    for t in tasks:
        dt_val = t["Task_Deadline"].replace("-", "")
        uid = f"task-{t['Task_ID']}-planner@syntriq"
        summary = f"[{t['Task_Subject']}] {t['Task_Title']} (Priority {t['Priority_Score']})"
        description = (
            f"Subject: {t['Task_Subject']}\\n"
            f"Priority Score: {t['Priority_Score']}\\n"
            f"Importance: {t['Task_Importance']}/5 | Difficulty: {t['Task_Difficulty']}/5\\n"
            f"Estimated Hours: {t['Estimated_Hours']} hrs"
        )
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_stamp}",
            f"DTSTART;VALUE=DATE:{dt_val}",
            f"DTEND;VALUE=DATE:{dt_val}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{description}",
            "STATUS:CONFIRMED",
            "TRANSP:TRANSPARENT",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    return Response(
        "\r\n".join(lines),
        mimetype="text/calendar",
        headers={"Content-Disposition": "attachment; filename=study_plan_schedule.ics"},
    )


@app.route("/api/tasks/<task_id>/subtasks", methods=["POST"])
@login_required
def add_subtask(task_id):
    data = request.get_json(silent=True) or request.form
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "Subtask title is required"}), 400
    try:
        subtask_id = store.add_subtask(g.user, get_db(), task_id, title)
        return jsonify({"success": True, "subtask_id": subtask_id, "title": title})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/subtasks/<subtask_id>/toggle", methods=["POST"])
@login_required
def toggle_subtask(subtask_id):
    if store.toggle_subtask(g.user, get_db(), subtask_id):
        return jsonify({"success": True})
    return jsonify({"error": "Subtask not found"}), 404


@app.route("/api/subtasks/<subtask_id>/delete", methods=["POST"])
@login_required
def delete_subtask(subtask_id):
    if store.delete_subtask(g.user, get_db(), subtask_id):
        return jsonify({"success": True})
    return jsonify({"error": "Subtask not found"}), 404


@app.route("/api/log-session", methods=["POST"])
@login_required
def log_session():
    data = request.get_json(silent=True) or request.form
    try:
        task_id = data.get("task_id") or None
        minutes = int(data.get("minutes", 25))
        session_id = store.log_study_session(g.user, get_db(), task_id, minutes)
        streak = store.get_study_streak(g.user, get_db())
        return jsonify({"success": True, "session_id": session_id, "streak": streak})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/active-session")
@login_required
def get_active_session_api():
    active = store.get_active_session(g.user, get_db())
    return jsonify(active or {"has_active": False})


@app.route("/api/time-tracking/start", methods=["POST"])
@login_required
def start_time_tracking():
    data = request.get_json(silent=True) or request.form
    try:
        task_id = data.get("task_id", "")
        force = bool(data.get("force", False) or data.get("force_switch", False))
        result = store.start_tracking_session(g.user, get_db(), task_id, force=force)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/time-tracking/pause", methods=["POST"])
@login_required
def pause_time_tracking():
    try:
        result = store.pause_tracking_session(g.user, get_db())
        return jsonify(result or {"paused": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/time-tracking/resume", methods=["POST"])
@login_required
def resume_time_tracking():
    try:
        result = store.resume_tracking_session(g.user, get_db())
        return jsonify(result or {"resumed": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/time-tracking/stop", methods=["POST"])
@login_required
def stop_time_tracking():
    try:
        result = store.stop_tracking_session(g.user, get_db())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/tasks/<task_id>/sessions")
@login_required
def get_task_sessions_api(task_id):
    try:
        sessions = store.get_task_sessions(g.user, get_db(), task_id)
        resp_tid = int(task_id) if str(task_id).isdigit() else task_id
        return jsonify({"task_id": resp_tid, "sessions": sessions, "total_sessions": len(sessions)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/time-intelligence")
@login_required
def time_intelligence():
    intel = store.get_time_intelligence_data(g.user, get_db())
    return render_template("time_intelligence.html", intel=intel)


@app.route("/api/time-intelligence")
@login_required
def api_time_intelligence():
    intel = store.get_time_intelligence_data(g.user, get_db())
    return jsonify(intel)


@app.route("/api/simulate-priority", methods=["POST"])
@login_required
def simulate_priority():
    data = request.get_json(silent=True) or request.form
    try:
        deadline_str = data.get("deadline")
        diff_val = int(data.get("difficulty", 3))
        imp_val = int(data.get("importance", 3))
        hours_val = float(data.get("estimated_hours", 2.0))
        days_shift = int(data.get("days_shift", 0))
        hours_shift = float(data.get("hours_shift", 0.0))

        base_date = parse_date(deadline_str)
        simulated_date = base_date + timedelta(days=days_shift)
        simulated_hours = max(0.5, hours_val + hours_shift)

        original_score = calculate_priority(base_date, diff_val, imp_val, hours_val)
        simulated_score = calculate_priority(simulated_date, diff_val, imp_val, simulated_hours)

        return jsonify({
            "original_score": original_score,
            "simulated_score": simulated_score,
            "score_diff": round(simulated_score - original_score, 2),
            "simulated_deadline": simulated_date.strftime("%Y-%m-%d"),
            "simulated_hours": simulated_hours,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/clear-all-tasks", methods=["POST"])
@login_required
def clear_all_tasks():
    store.clear_all_tasks(g.user, get_db())
    flash("All tasks in your personal workspace have been deleted.", "info")
    return redirect(url_for("dashboard"))


@app.route("/seed-sample-tasks", methods=["POST"])
@login_required
def seed_sample_tasks():
    store.clear_all_tasks(g.user, get_db())
    today = date.today()
    samples = [
        ("Mathematics Calculus Problem Set", "Mathematics", (today + timedelta(days=1)).strftime("%Y-%m-%d"), 4, 5, 3.0),
        ("Physics Internal Assessment Draft", "Physics", (today + timedelta(days=2)).strftime("%Y-%m-%d"), 5, 5, 6.5),
        ("Chemistry Chapter 4 Reading", "Chemistry", (today - timedelta(days=1)).strftime("%Y-%m-%d"), 2, 4, 1.5),
        ("English Literature Essay on Hamlet", "English Literature", (today + timedelta(days=5)).strftime("%Y-%m-%d"), 4, 4, 4.0),
        ("Spanish Vocabulary Flashcards", "Spanish", (today + timedelta(days=12)).strftime("%Y-%m-%d"), 2, 2, 1.0),
    ]
    for title, subj, dl, d, i, h in samples:
        store.add_task(g.user, get_db(), title=title, subject=subj, deadline=dl, difficulty=d, importance=i, estimated_hours=h)
    flash("Sample tasks loaded into your workspace.", "info")
    return redirect(url_for("dashboard"))


@app.route("/reset-database", methods=["POST"])
@login_required
def reset_database():
    return clear_all_tasks()


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
