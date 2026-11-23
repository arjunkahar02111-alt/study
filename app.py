"""
Smart Study Planner - Flask Web Application
Implements Criterion A (Problem Specification) and Criterion B (Design).
"""

import os
from datetime import date, datetime, timedelta, timezone
import random
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    Response,
    send_from_directory
)

import database
from priority_calculator import calculate_priority, is_overdue, parse_date

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "smart-study-planner-secret-key-2026")

# Database path
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "study_planner.db")

MOTIVATIONAL_QUOTES = [
    {"quote": "It always seems impossible until it's done.", "author": "Nelson Mandela"},
    {"quote": "Live as if you were to die tomorrow. Learn as if you were to live forever.", "author": "Mahatma Gandhi"},
    {"quote": "Success is the sum of small efforts, repeated day in and day out.", "author": "Robert Collier"},
    {"quote": "The expert in anything was once a beginner.", "author": "Helen Hayes"},
    {"quote": "Don't watch the clock; do what it does. Keep going.", "author": "Sam Levenson"},
    {"quote": "Nothing in life is to be feared, it is only to be understood.", "author": "Marie Curie"},
    {"quote": "You don't have to be great to start, but you have to start to be great.", "author": "Zig Ziglar"}
]


def setup_application():
    """Initializes the database without forcing seed tasks."""
    database.init_db(DB_FILE)


# Ensure DB exists on startup
setup_application()


@app.context_processor
def inject_today():
    """Injects current date and helper statistics into all Jinja templates."""
    today = date.today()
    return {"current_date": today}


@app.route("/")
@app.route("/dashboard")
def dashboard():
    """
    Dashboard (Main Page):
    - View summary cards: Total, Pending, Completed, Overdue, Upcoming deadlines
    - View filtered task lists based on query parameter
    - Provides direct actions to add tasks, open study plan, complete/edit/delete tasks
    """
    filter_type = request.args.get("filter", "all").lower()

    all_tasks = database.get_all_tasks(DB_FILE)
    pending_tasks = database.get_pending_tasks(DB_FILE)
    completed_tasks = database.get_completed_tasks(DB_FILE)
    overdue_tasks = database.get_overdue_tasks(DB_FILE)
    upcoming_tasks = database.get_upcoming_tasks(days_ahead=7, db_path=DB_FILE)

    # Select tasks to show in the main table based on filter
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

    streak = database.get_study_streak(DB_FILE)
    capacity = database.get_daily_capacity(DB_FILE)
    heatmap = database.get_weekly_workload_heatmap(DB_FILE)
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
        quote=quote
    )


@app.route("/add-task", methods=["GET", "POST"])
def add_task():
    """
    Add Task Page:
    Allows user to input title, subject, deadline, difficulty, importance, estimated hours.
    Validates according to Criterion B pseudocode and calculates priority score.
    """
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        subject = request.form.get("subject", "").strip()
        deadline = request.form.get("deadline", "").strip()
        difficulty = request.form.get("difficulty", "").strip()
        importance = request.form.get("importance", "").strip()
        estimated_hours = request.form.get("estimated_hours", "").strip()

        # Validation per pseudocode:
        # IF title IS EMPTY OR subject IS EMPTY OR deadline IS EMPTY THEN
        if not title or not subject or not deadline:
            flash("Please complete all required fields", "danger")
            return render_template("add_task.html", form_data=request.form), 400

        try:
            diff_int = int(difficulty)
            imp_int = int(importance)
            hours_float = float(estimated_hours)
        except (ValueError, TypeError):
            flash("Invalid input", "danger")
            return render_template("add_task.html", form_data=request.form), 400

        # IF difficulty < 1 OR difficulty > 5 OR importance < 1 OR importance > 5 OR estimated_hours <= 0 THEN
        if diff_int < 1 or diff_int > 5 or imp_int < 1 or imp_int > 5 or hours_float <= 0:
            flash("Invalid input", "danger")
            return render_template("add_task.html", form_data=request.form), 400

        try:
            parse_date(deadline)
        except Exception:
            flash("Invalid deadline format. Please select a valid date.", "danger")
            return render_template("add_task.html", form_data=request.form), 400

        try:
            task_id = database.add_task(
                title=title,
                subject=subject,
                deadline=deadline,
                difficulty=diff_int,
                importance=imp_int,
                estimated_hours=hours_float,
                db_path=DB_FILE
            )
            flash("Task added successfully", "success")
            return redirect(url_for("study_plan"))
        except Exception as e:
            flash(f"Error adding task: {str(e)}", "danger")
            return render_template("add_task.html", form_data=request.form), 500

    return render_template("add_task.html", form_data={})


@app.route("/study-plan")
def study_plan():
    """
    Study Plan Page:
    Displays all pending tasks sorted by Priority Score in descending order.
    Shows score breakdown, urgency, workload, overdue tags, and action controls.
    """
    tasks = database.get_study_plan(DB_FILE)
    completed_tasks = database.get_completed_tasks(DB_FILE)
    return render_template(
        "study_plan.html",
        tasks=tasks,
        completed_tasks=completed_tasks
    )


@app.route("/edit-task/<int:task_id>", methods=["GET", "POST"])
def edit_task(task_id):
    """
    Edit Task Page:
    Loads existing task, validates changes, recalculates priority score and updates database.
    """
    task = database.get_task_by_id(task_id, DB_FILE)
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
            hours_float = float(estimated_hours)
        except (ValueError, TypeError):
            flash("Invalid input", "danger")
            return render_template("edit_task.html", task=task, form_data=request.form), 400

        if diff_int < 1 or diff_int > 5 or imp_int < 1 or imp_int > 5 or hours_float <= 0:
            flash("Invalid input", "danger")
            return render_template("edit_task.html", task=task, form_data=request.form), 400

        try:
            parse_date(deadline)
        except Exception:
            flash("Invalid deadline date", "danger")
            return render_template("edit_task.html", task=task, form_data=request.form), 400

        try:
            database.update_task(
                task_id=task_id,
                title=title,
                subject=subject,
                deadline=deadline,
                difficulty=diff_int,
                importance=imp_int,
                estimated_hours=hours_float,
                status=status,
                db_path=DB_FILE
            )
            flash("Task updated successfully", "success")
            return redirect(url_for("study_plan"))
        except Exception as e:
            flash(f"Error updating task: {str(e)}", "danger")
            return render_template("edit_task.html", task=task, form_data=request.form), 500

    return render_template("edit_task.html", task=task, form_data=task)


@app.route("/complete-task/<int:task_id>", methods=["POST"])
def complete_task(task_id):
    """Marks task as completed."""
    success = database.complete_task(task_id, DB_FILE)
    if success:
        flash("Task marked as completed", "success")
    else:
        flash("Task not found", "danger")

    redirect_to = request.referrer or url_for("study_plan")
    return redirect(redirect_to)


@app.route("/delete-task/<int:task_id>", methods=["POST"])
def delete_task(task_id):
    """Deletes task from database."""
    success = database.delete_task(task_id, DB_FILE)
    if success:
        flash("Task deleted successfully", "success")
    else:
        flash("Task not found", "danger")

    redirect_to = request.referrer or url_for("dashboard")
    return redirect(redirect_to)


@app.route("/api/preview-priority", methods=["POST"])
def preview_priority():
    """
    Live priority calculation API for client-side dynamic feedback.
    Returns urgency, workload, and overall priority score.
    """
    data = request.get_json(silent=True) or request.form
    try:
        deadline = data.get("deadline")
        difficulty = int(data.get("difficulty", 3))
        importance = int(data.get("importance", 3))
        estimated_hours = float(data.get("estimated_hours", 2.0))

        if not deadline:
            return jsonify({"error": "Deadline required"}), 400

        score = calculate_priority(deadline, difficulty, importance, estimated_hours)
        overdue = is_overdue(deadline)
        return jsonify({
            "priority_score": score,
            "is_overdue": overdue
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/export/calendar.ics")
def export_calendar():
    """
    Exports all pending tasks as an RFC-5545 iCalendar (.ics) file.
    Can be directly imported into Google Calendar, Apple Calendar, or Outlook.
    """
    tasks = database.get_pending_tasks(DB_FILE)
    
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Smart Study Planner//Priority Task Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Smart Study Planner Schedule"
    ]
    
    now_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    
    for t in tasks:
        # Format date for all-day event
        dt_val = t["Task_Deadline"].replace("-", "")
        uid = f"task-{t['Task_ID']}-planner@smartstudy"
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
            "END:VEVENT"
        ])
        
    lines.append("END:VCALENDAR")
    ics_content = "\r\n".join(lines)
    
    return Response(
        ics_content,
        mimetype="text/calendar",
        headers={"Content-Disposition": "attachment; filename=study_plan_schedule.ics"}
    )


@app.route("/api/tasks/<int:task_id>/subtasks", methods=["POST"])
def add_subtask(task_id):
    """Adds a subtask to an existing assignment."""
    data = request.get_json(silent=True) or request.form
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "Subtask title is required"}), 400
    try:
        subtask_id = database.add_subtask(task_id, title, DB_FILE)
        return jsonify({"success": True, "subtask_id": subtask_id, "title": title})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/subtasks/<int:subtask_id>/toggle", methods=["POST"])
def toggle_subtask(subtask_id):
    """Toggles completion status of a subtask."""
    success = database.toggle_subtask(subtask_id, DB_FILE)
    if success:
        return jsonify({"success": True})
    return jsonify({"error": "Subtask not found"}), 404


@app.route("/api/subtasks/<int:subtask_id>/delete", methods=["POST"])
def delete_subtask(subtask_id):
    """Deletes a subtask."""
    success = database.delete_subtask(subtask_id, DB_FILE)
    if success:
        return jsonify({"success": True})
    return jsonify({"error": "Subtask not found"}), 404


@app.route("/api/log-session", methods=["POST"])
def log_session():
    """Logs a completed study focus session."""
    data = request.get_json(silent=True) or request.form
    try:
        task_id = data.get("task_id")
        task_id = int(task_id) if task_id else None
        minutes = int(data.get("minutes", 25))
        session_id = database.log_study_session(task_id, minutes, DB_FILE)
        streak = database.get_study_streak(DB_FILE)
        return jsonify({"success": True, "session_id": session_id, "streak": streak})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/simulate-priority", methods=["POST"])
def simulate_priority():
    """
    Simulation API: Takes base task values and hypothetical shifts in deadline and hours,
    returns the simulated score, urgency, workload, and difference.
    """
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
            "simulated_hours": simulated_hours
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/clear-all-tasks", methods=["POST"])
def clear_all_tasks():
    """Clears all tasks from database so the user can test with a clean slate."""
    database.clear_all_tasks(DB_FILE)
    flash("All previous tasks have been deleted. You can now test with your own inputs!", "info")
    return redirect(url_for("dashboard"))


@app.route("/seed-sample-tasks", methods=["POST"])
def seed_sample_tasks():
    """Loads sample tasks for demonstration."""
    database.clear_all_tasks(DB_FILE)
    database.seed_sample_tasks(DB_FILE)
    flash("Sample tasks loaded successfully.", "info")
    return redirect(url_for("dashboard"))


@app.route("/reset-database", methods=["POST"])
def reset_database():
    """Clears all tasks."""
    return clear_all_tasks()


@app.route("/favicon.ico")
def favicon():
    """Serves the standard favicon.ico file."""
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon"
    )


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
