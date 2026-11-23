# SYNTRIQ 3.0 — Application Security & Data Integrity Specifications

## 1. Executive Summary & Threat Model

Security and data integrity in SYNTRIQ 3.0 are foundational requirements. The application manages academic schedules, task deadlines, and personal productivity data. This document outlines the security architecture, input validation rules, SQL injection defenses, cross-site scripting (XSS) protections, CSRF mitigation, session handling, and database integrity invariants.

---

## 2. Core Security Invariants

1. **Zero SQL Injection**: 100% of database queries use parameterized SQL statements with placeholder bindings (`?`). Dynamic string concatenation in SQL queries is strictly prohibited.
2. **Defensive Input Validation**: Every incoming user payload is validated on both frontend (instant feedback) and backend (strict enforcement).
3. **Cross-Site Scripting (XSS) Prevention**: All user-supplied strings are auto-escaped by the Jinja2 templating engine. Raw HTML injection is blocked.
4. **Destructive Action Confirmation**: Deletion and database clearing operations require explicit user confirmation and operate solely via `POST` HTTP requests.
5. **Data Isolation & Integrity**: Foreign key constraints and database `CHECK` constraints enforce data validity at the storage engine level.
6. **No Exposed Secrets**: Zero API keys, credentials, or private tokens exist in client-side code or public version control.

---

## 3. Input Validation & Type Enforcement

All task creation and update requests undergo rigorous validation in `app.py` and `database.py`:

```python
# Validation per Criterion B specifications:
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

# Boundary checks
if diff_int < 1 or diff_int > 5 or imp_int < 1 or imp_int > 5 or hours_float <= 0:
    flash("Invalid input", "danger")
    return render_template("add_task.html", form_data=request.form), 400

try:
    parse_date(deadline)
except Exception:
    flash("Invalid deadline format. Please select a valid date.", "danger")
    return render_template("add_task.html", form_data=request.form), 400
```

### Validation Matrix
| Field | Type | Required | Constraints | Sanitization / Handling |
| :--- | :---: | :---: | :--- | :--- |
| `Task_Title` | `TEXT` | Yes | Non-empty, stripped | Trimmed, escaped in HTML |
| `Task_Subject` | `TEXT` | Yes | Non-empty, stripped | Trimmed, escaped in HTML |
| `Task_Deadline` | `TEXT` | Yes | Format `YYYY-MM-DD`, valid date | Validated via `datetime.strptime` |
| `Task_Difficulty` | `INTEGER` | Yes | $1 \le \text{Difficulty} \le 5$ | Integer cast, boundary checked |
| `Task_Importance` | `INTEGER` | Yes | $1 \le \text{Importance} \le 5$ | Integer cast, boundary checked |
| `Estimated_Hours` | `REAL` | Yes | $\text{Hours} > 0.0$ | Float cast, strictly positive |
| `Subtask_Title` | `TEXT` | Yes | Non-empty, stripped | Trimmed, escaped in HTML |

---

## 4. SQL Injection Protection

SQLite relational database queries are executed using parameterized binding:

```python
# Secure query execution in database.py
conn.execute("""
    INSERT INTO Tasks (
        Task_Title, Task_Subject, Task_Deadline,
        Task_Difficulty, Task_Importance, Estimated_Hours,
        Priority_Score, Task_Status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", (title, subject, formatted_deadline, diff_val, imp_val, hours_val, priority_score, status))
```

### Database Schema Invariants & Foreign Key Constraints
```sql
PRAGMA foreign_keys = ON;

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

CREATE TABLE IF NOT EXISTS Subtasks (
    Subtask_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Task_ID INTEGER NOT NULL,
    Subtask_Title TEXT NOT NULL,
    Is_Completed INTEGER NOT NULL DEFAULT 0 CHECK (Is_Completed IN (0, 1)),
    FOREIGN KEY (Task_ID) REFERENCES Tasks(Task_ID) ON DELETE CASCADE
);
```

---

## 5. XSS Defense & Template Safety

* **Jinja2 Autoescaping**: Enabled by default for all `.html` templates. Characters `&`, `<`, `>`, `"`, and `'` are automatically converted to their safe HTML entity representations.
* **JavaScript DOM Injections**: Dynamic updates use `.textContent` for untrusted user inputs (such as task titles and subjects) rather than `.innerHTML`, eliminating DOM-based XSS attack vectors.

---

## 6. HTTP Methods & State Modification Protections

* **Destructive Operations**: Task deletion (`/delete-task/<id>`), task completion (`/complete-task/<id>`), subtask creation/toggle/deletion, and database clearing (`/clear-all-tasks`) strictly require HTTP `POST` requests.
* **GET Requests are Idempotent**: Navigating via `GET` never deletes, completes, or modifies persistent task records.
* **Safe Error Handling**: Server errors return standard HTTP error statuses (`400 Bad Request`, `404 Not Found`, `500 Internal Error`) with user-friendly error banners. Raw database tracebacks, file paths, and environment internals are never rendered in client templates.

---

## 7. Client Security & Data Storage

* **Local Storage Usage**: `localStorage` is restricted strictly to non-sensitive UI preferences:
  * `localStorage["planner_sound_fx"]`: Boolean sound toggle preference.
  * No tokens, passwords, or personal academic records are stored in unencrypted browser storage.
* **Calendar Export Safety**: The iCalendar export (`/export/calendar.ics`) produces RFC-5545 compliant calendar content with sanitized line endings and escaped description fields, preventing iCalendar injection.
