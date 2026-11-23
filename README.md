# 📚 Smart Study Planner - Automated Priority Web Application

An intelligent, algorithmic study planning web application built using **Python (Flask)**, **SQLite**, and modern **HTML5/CSS3/JavaScript**.

Developed in direct alignment with **Criterion A (Problem Specification)** and **Criterion B (Design)** for Computer Science coursework.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+ (Tested on Python 3.13)
- Flask (Installed: `pip install flask`)

### 2. Run the Application
Open your terminal in this directory (`E:\Aasu`) and run:
```bash
python app.py
```

### 3. Open in Browser
Visit:
```
http://127.0.0.1:5000
```
or click: [http://localhost:5000](http://localhost:5000)

### 4. Run the Automated Test Suite (Criterion D Verification)
To execute all 14 test cases from Criterion B's Test Plan:
```bash
python run_tests.py
```
All 14 tests run automatically and output a formatted markdown table ready for your Criterion D documentation.

---

## 📁 Project Structure

```
E:\Aasu\
│
├── app.py                     # Flask web server, route definitions, error handling
├── database.py                # SQLite database management, CRUD operations, transactions
├── priority_calculator.py     # Algorithmic priority score logic & date computations
├── test_study_planner.py      # Comprehensive test suite covering all 14 test cases
├── run_tests.py               # Automated test runner with formatted Criterion D table
├── study_planner.db           # Relational SQLite database with sample student tasks
├── README.md                  # Quick start and project overview
├── PROJECT_DOCUMENTATION.md   # Complete Criteria A to E coursework report
│
├── templates/                 # Jinja2 HTML5 Templates
│   ├── base.html              # Base layout, responsive navigation bar, flash messages, footer
│   ├── dashboard.html         # Dashboard with metrics cards, filters, and task management
│   ├── add_task.html          # Add Task form with real-time algorithm preview
│   ├── edit_task.html         # Edit Task form with pre-populated values and recalculation
│   └── study_plan.html        # Prioritized study plan sorted descending by Priority Score
│
└── static/
    ├── css/
    │   └── style.css          # Modern, responsive stylesheet with priority color coding
    └── js/
        └── main.js            # Real-time client-side priority calculation preview & alerts
```

---

## 🧮 Computational Thinking & Priority Algorithm

The priority score is computed dynamically using 4 weighted parameters:

$$\text{Priority Score} = (0.4 \times \text{Urgency}) + (0.3 \times \text{Importance}) + (0.2 \times \text{Difficulty}) + (0.1 \times \text{Workload})$$

### 1. Urgency Score (Weight: 40%)
Calculated dynamically from the days remaining until the deadline ($\Delta t = \text{Deadline} - \text{Current Date}$):
- $\Delta t \le 1$ day (or overdue): **Urgency = 5**
- $\Delta t \le 3$ days: **Urgency = 4**
- $\Delta t \le 7$ days: **Urgency = 3**
- $\Delta t \le 14$ days: **Urgency = 2**
- $\Delta t > 14$ days: **Urgency = 1**

### 2. Importance Score (Weight: 30%)
Input by the student on a scale of **1 to 5** (1: Optional/Minor, 5: Critical/Final Exam/IA).

### 3. Difficulty Level (Weight: 20%)
Input by the student on a scale of **1 to 5** (1: Very Easy Review, 5: Very Hard/Complex).

### 4. Workload Score (Weight: 10%)
Derived from estimated completion time in hours ($H$):
- $H \ge 6.0$ hours: **Workload = 5**
- $H \ge 4.0$ hours: **Workload = 4**
- $H \ge 2.0$ hours: **Workload = 3**
- $H \ge 1.0$ hours: **Workload = 2**
- $H < 1.0$ hours: **Workload = 1**

The final composite score ranges from **1.00 to 5.00** and is rounded to two decimal places.

---

## ⚡ Interactive Pro Features & Engagement Tools

1. **⚡ Focus Kitchen Pomodoro Timer**:
   - 25m study / 50m deep work / 5m break circular SVG progress countdown.
   - Built-in Web Audio API acoustic chimes & ambient soundscapes (Rain, Coffee Shop, White Noise) — 100% offline, zero external dependencies.
   - Direct task linking from the Study Plan (#1 priority task).

2. **🎛️ Interactive "What-If" Priority Simulator**:
   - Live sliders for deadline shifts (-3d to +14d) and hours adjustment (-4h to +6h).
   - Real-time recalculation of simulated priority scores and rank ripple effects.

3. **📋 Subtask Milestones & Decomposition**:
   - Break large assignments into bite-sized actionable steps.
   - Check off mini-steps with live progress indicators.

4. **📅 1-Click Calendar Sync (.ics Export)**:
   - Export all pending assignments and priorities directly to **Google Calendar**, **Apple Calendar**, or **Outlook**.

5. **🗓️ 7-Day Workload Density Heatmap**:
   - Visual intensity chips highlighting crunch periods before they happen.

6. **⚡ Daily Workload Capacity Meter**:
   - Automatic overload warning when scheduled tasks exceed recommended 6.0 hours/day.

7. **🎉 Confetti Celebration & Acoustic Chimes**:
   - Interactive celebratory particle explosions upon completing assignments and focus sessions.

8. **⚡ Smart Date Quick Chips & Keyboard Shortcuts**:
   - `Today`, `Tomorrow`, `In 3 Days`, `Next Week` quick chips.
   - Shortcuts: <kbd>N</kbd> (New Task), <kbd>D</kbd> (Dashboard), <kbd>S</kbd> (Study Plan), <kbd>P</kbd> (Focus Timer), <kbd>Space</kbd> (Play/Pause Timer), <kbd>Esc</kbd> (Close).

9. **📱 100% Mobile & Device Responsive**:
   - Automatic mobile layout adjustments, iOS zoom-lock prevention (`font-size: 16px`), and touch-optimized action targets.

10. **🖨️ Physical Study Sheet Print Mode**:
    - Dedicated print stylesheet (`@media print`) generating clean, ink-friendly checklists.


| Column Name | SQL Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `Task_ID` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Unique identifier for each task |
| `Task_Title` | `TEXT` | `NOT NULL` | Descriptive title of assignment |
| `Task_Subject` | `TEXT` | `NOT NULL` | Course or topic name |
| `Task_Deadline`| `TEXT` | `NOT NULL` (YYYY-MM-DD) | Due date for the task |
| `Task_Difficulty`| `INTEGER` | `CHECK (1 TO 5)` | Difficulty rating |
| `Task_Importance`| `INTEGER` | `CHECK (1 TO 5)` | Importance rating |
| `Estimated_Hours`| `REAL` | `CHECK (> 0)` | Time required in hours |
| `Priority_Score` | `REAL` | `NOT NULL` | Calculated composite score |
| `Task_Status` | `TEXT` | `'Pending'` / `'Completed'` | Completion status |

---

## 🧪 Test Plan & Verification (Criterion D)

All 14 test cases passed successfully:

| # | Feature | Test Case | Expected Outcome | Actual Outcome | Status |
| :-: | :--- | :--- | :--- | :--- | :-: |
| 1 | Add task | Enter valid task details | Task saved in database | Task saved with ID & correct attributes | **PASSED** |
| 2 | Input validation | Submit empty required fields | Error message displayed | Returns 400 with flash warning | **PASSED** |
| 3 | Difficulty validation | Value outside 1–5 | System rejects invalid value | Rejection verified at DB & route level | **PASSED** |
| 4 | Importance validation | Value outside 1–5 | System rejects invalid value | Rejection verified at DB & route level | **PASSED** |
| 5 | Priority calculation | Known test values | Correct score computed | Math verified ($4.6$ and $1.9$) | **PASSED** |
| 6 | Task sorting | Tasks with different scores | Descending priority order | Sorted strictly descending | **PASSED** |
| 7 | Edit task | Change deadline/difficulty | Updated & recalculated | Saved and score updated dynamically | **PASSED** |
| 8 | Delete task | Delete existing task | Removed from database | Row deleted, verify returns None | **PASSED** |
| 9 | Complete task | Mark pending as completed | Status changes to Completed | Status successfully updated | **PASSED** |
| 10 | Overdue tasks | Task with past deadline | Labelled as overdue | Overdue flag & days late computed | **PASSED** |
| 11 | Upcoming deadlines | Tasks with approaching dates| Filtered within 7 days | Displayed in upcoming query | **PASSED** |
| 12 | Data storage | Reconnect / page reload | Tasks persist in DB | Data persists permanently | **PASSED** |
| 13 | Study plan | Multiple pending tasks | Organized plan generated | Ranked with breakdown & actions | **PASSED** |
| 14 | User interface | Navigate between views | Smooth navigation (200 OK) | All routes active and rendered | **PASSED** |
