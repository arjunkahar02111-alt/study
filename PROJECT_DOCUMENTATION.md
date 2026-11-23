# Smart Study Planner - Complete Project Documentation
**Coursework Criteria Report: Criteria A through E**

---

# Criterion A: Problem Specification

## 1. Problem Statement
As a student managing multiple subjects and assignments, I often find it difficult to organize my study time effectively. Each task has different deadlines, levels of difficulty, and importance, making it challenging to decide what to prioritize. Currently, I rely on basic tools such as planners or to-do lists, which only allow me to record tasks but do not help in prioritizing them.

This often leads to poor time management, where less important tasks are completed first while urgent ones are delayed. As a result, deadlines may be missed and stress increases. Existing productivity tools also require manual prioritization and do not automatically adjust based on urgency or workload.

To solve this problem, I will develop a **Smart Study Planner** that allows users to input tasks with details such as deadlines, difficulty, and importance. The system will then calculate a priority score and generate an organized study plan, helping students manage their time more efficiently.

## 2. Computational Thinking Rationale and Justification
- **Decomposition**: Breaking down the overall system into modular sub-problems: user input and validation, priority score computation, database CRUD operations, and study plan scheduling.
- **Abstraction**: Isolating key task variables—urgency (days remaining), importance, difficulty, and workload (estimated hours)—to model task priority mathematically without unnecessary overhead.
- **Pattern Recognition**: Observing that approaching deadlines exponentially increase study urgency, and combining this with task complexity to structure an automated sorting pipeline.
- **Algorithmic Design**: Formulating an objective mathematical weighted algorithm:
  $$\text{Priority Score} = 0.4 \times \text{Urgency} + 0.3 \times \text{Importance} + 0.2 \times \text{Difficulty} + 0.1 \times \text{Workload}$$
- **Tool Choice Justification**:
  - **Python**: Robust backend processing, native date-time handling, mathematical calculation, and simple integration with SQLite.
  - **Flask**: Lightweight web framework that enables browser access without complex installations.
  - **SQLite / SQL**: Reliable relational database ensuring ACID-compliant task storage, efficient sorting (`ORDER BY Priority_Score DESC`), and quick retrieval.

## 3. Success Criteria
1. Users can add tasks with all required details.
2. Tasks are stored in the database.
3. Users can edit and delete tasks.
4. The website automatically calculates task priority.
5. Tasks are sorted by priority.
6. Overdue and upcoming tasks are clearly shown.
7. Users can mark tasks as completed.
8. The website generates an organized study plan.
9. Invalid inputs display clear error messages.
10. The website has a simple, user-friendly interface.
11. The website correctly saves and retrieves task data.
12. The website works smoothly without major errors.

---

# Criterion B: Design

## 1. Website Structure
The website consists of three core pages:
- **Dashboard**: High-level overview, statistics cards (Total, Pending, Overdue, Upcoming, Completed), filtered task views, quick action buttons.
- **Add Task Page**: Input form for task parameters with real-time algorithm preview.
- **Study Plan Page**: Dynamic study schedule sorted descending by priority score, displaying individual factor weights and task status.
- **Edit Task Page**: Pre-populated update form that recalculates priority scores upon modification.

## 2. System Flow
```
Start
  │
  ▼
Open Website (Dashboard)
  │
  ▼
Add / Edit Task ──► Enter Details (Title, Subject, Deadline, Diff, Imp, Hours)
  │
  ▼
Validate Inputs?
  ├─ No  ──► Display Error Message ──► Return to Form
  └─ Yes ──► Calculate Urgency, Workload & Priority Score
               │
               ▼
             Save / Update Record in SQLite Database
               │
               ▼
             Retrieve Pending Tasks
               │
               ▼
             Sort by Priority_Score (DESC)
               │
               ▼
             Display Dynamic Study Plan
               │
               ▼
             User Completes, Edits, or Deletes Task
               │
               ▼
             Database Updated & Views Refreshed
```

## 3. Database Structure (`Tasks` Table)
| Field Name | Data Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `Task_ID` | `INTEGER` | Primary Key, Auto-increment | 1 |
| `Task_Title` | `VARCHAR/TEXT` | Name of task | Mathematics homework |
| `Task_Subject` | `VARCHAR/TEXT` | Subject of task | Mathematics |
| `Task_Deadline` | `DATE/TEXT` | Deadline date (YYYY-MM-DD) | 2026-10-05 |
| `Task_Difficulty` | `INTEGER` | Difficulty rating (1 to 5) | 4 |
| `Task_Importance` | `INTEGER` | Importance rating (1 to 5) | 5 |
| `Estimated_Hours` | `REAL` | Estimated completion hours | 3.0 |
| `Priority_Score` | `REAL` | Calculated priority score | 4.20 |
| `Task_Status` | `VARCHAR/TEXT` | 'Pending' or 'Completed' | Pending |

---

# Criterion C: Development

## 1. Modular Architecture
The solution is organized into modular files:
- `priority_calculator.py`: Pure algorithmic logic isolated from UI, enabling automated unit testing.
- `database.py`: Encapsulates all SQL statements (`INSERT`, `SELECT`, `UPDATE`, `DELETE`) and SQLite connection management.
- `app.py`: Flask routing, controller logic, HTTP session flash messages, and template rendering.
- `templates/` & `static/`: Accessible, responsive front-end with live dynamic JavaScript calculation preview.

## 2. Key Code Implementations

### Priority Calculation (`priority_calculator.py`)
```python
def calculate_priority(deadline, difficulty, importance, estimated_hours, current_date=None):
    if current_date is None:
        current_date = date.today()
    
    # 1. Calculate days remaining
    deadline_date = parse_date(deadline)
    days = (deadline_date - current_date).days

    # 2. Urgency mapping
    if days <= 1: urgency = 5
    elif days <= 3: urgency = 4
    elif days <= 7: urgency = 3
    elif days <= 14: urgency = 2
    else: urgency = 1

    # 3. Workload mapping
    hours = float(estimated_hours)
    if hours >= 6.0: workload = 5
    elif hours >= 4.0: workload = 4
    elif hours >= 2.0: workload = 3
    elif hours >= 1.0: workload = 2
    else: workload = 1

    # 4. Weighted formula
    score = (0.4 * urgency) + (0.3 * int(importance)) + (0.2 * int(difficulty)) + (0.1 * workload)
    return round(score, 2)
```

### Dynamic Study Plan Generation (`database.py`)
```python
def get_study_plan(db_path, current_date=None):
    if current_date is None:
        current_date = date.today()

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Tasks WHERE Task_Status = 'Pending'")
    rows = cursor.fetchall()

    tasks = []
    for row in rows:
        task = dict(row)
        # Dynamic recalculation as calendar days advance
        score = calculate_priority(
            task["Task_Deadline"], task["Task_Difficulty"],
            task["Task_Importance"], task["Estimated_Hours"],
            current_date=current_date
        )
        task["Priority_Score"] = score
        tasks.append(_format_task_dict(task, current_date))
    
    # Sort descending by priority score
    tasks.sort(key=lambda t: (-t["Priority_Score"], t["Task_Deadline"]))
    return tasks
```

## 3. Robust Input Validation & Error Handling
Validation occurs at two levels:
1. **Application/Controller level (`app.py`)**: Checks for empty strings, non-numeric values, and out-of-bound ranges ($1 \le \text{diff} \le 5$, $1 \le \text{imp} \le 5$, $\text{hours} > 0$), returning HTTP 400 with user-friendly flash messages.
2. **Database Schema level (`database.py`)**: SQLite `CHECK` constraints guarantee database integrity even under external operations.

---

# Criterion D: Functionality and Test Results

All 14 test cases specified in the Criterion B Test Plan were implemented and verified using the automated test suite (`run_tests.py`):

| # | Feature | Test Case | Expected Outcome | Actual Outcome | Fixes Needed |
| :-: | :--- | :--- | :--- | :--- | :--- |
| **1** | Add task | Enter valid task details | Task should be saved in the database | **PASSED** - Task correctly inserted and retrieved with generated `Task_ID` | None - Functioning as expected |
| **2** | Input validation | Submit form with empty required fields | System should display an error message | **PASSED** - System returned HTTP 400 and rejected blank submission | None - Functioning as expected |
| **3** | Difficulty validation | Enter difficulty outside 1–5 | System should reject the invalid value | **PASSED** - Values < 1 or > 5 rejected at DB and controller layer | None - Functioning as expected |
| **4** | Importance validation | Enter importance outside 1–5 | System should reject the invalid value | **PASSED** - Values < 1 or > 5 rejected at DB and controller layer | None - Functioning as expected |
| **5** | Priority calculation | Enter known task values | System should calculate correct priority score | **PASSED** - Algorithm produced exact mathematical score ($4.6$ and $1.9$) | None - Functioning as expected |
| **6** | Task sorting | Add tasks with different priority scores | Tasks displayed in descending priority order | **PASSED** - Query returned tasks sorted from highest to lowest score | None - Functioning as expected |
| **7** | Edit task | Change deadline of existing task | Updated info saved and priority recalculated | **PASSED** - Priority score recalculated immediately from new parameters | None - Functioning as expected |
| **8** | Delete task | Delete an existing task | Task should be removed from database | **PASSED** - Task record permanently removed from SQLite database | None - Functioning as expected |
| **9** | Complete task | Mark a pending task as completed | Task status should change to completed | **PASSED** - Status changed to 'Completed', excluded from pending study plan | None - Functioning as expected |
| **10**| Overdue tasks | Add task with past deadline | Task should be labelled as overdue | **PASSED** - System flagged `is_overdue=True` with late badge | None - Functioning as expected |
| **11**| Upcoming deadlines | Add tasks with approaching deadlines | Upcoming tasks displayed clearly | **PASSED** - Filter correctly selected tasks within 7 days | None - Functioning as expected |
| **12**| Data storage | Refresh website after adding tasks | Saved tasks should remain available | **PASSED** - SQLite persists tasks across application restarts | None - Functioning as expected |
| **13**| Study plan | Add multiple pending tasks | Organized study plan should be generated | **PASSED** - Plan generated with ranking, factor breakdowns, and actions | None - Functioning as expected |
| **14**| User interface | Navigate between dashboard, form, and plan | Pages work correctly and easy to navigate | **PASSED** - All routes returned HTTP 200 with proper responsive templates | None - Functioning as expected |

**Summary: 14 out of 14 test cases PASSED (100% success rate).**

---

# Criterion E: Evaluation

## 1. Evaluation Against Success Criteria
| Success Criterion | Status | Evidence in Implemented Solution |
| :--- | :---: | :--- |
| 1. Users can add tasks with all required details | **MET** | Add Task form supports Title, Subject, Deadline, Difficulty, Importance, and Estimated Hours. |
| 2. Tasks are stored in the database | **MET** | Relational SQLite table `Tasks` stores records with primary keys and constraints. |
| 3. Users can edit and delete tasks | **MET** | Edit Task form allows full updates; Delete action removes records with confirmation. |
| 4. The website automatically calculates task priority | **MET** | Weighted formula calculates composite score between 1.00 and 5.00 automatically. |
| 5. Tasks are sorted by priority | **MET** | Study Plan page lists pending tasks strictly in descending order of Priority Score. |
| 6. Overdue and upcoming tasks are clearly shown | **MET** | Overdue tasks are tagged with prominent badges; Upcoming deadlines filter isolates 7-day tasks. |
| 7. Users can mark tasks as completed | **MET** | One-click complete action moves tasks from Pending to Completed history. |
| 8. The website generates an organized study plan | **MET** | Study Plan view displays ranked cards with factor breakdowns (Urgency, Workload, Diff, Imp). |
| 9. Invalid inputs display clear error messages | **MET** | Form alerts and flash notifications warn users of missing or out-of-range inputs. |
| 10. The website has a simple, user-friendly interface | **MET** | Responsive clean layout, modern cards, visual badges, and live preview on Add/Edit forms. |
| 11. The website correctly saves and retrieves task data | **MET** | Persistent SQLite database reloads records across server reboots without data loss. |
| 12. The website works smoothly without major errors | **MET** | 100% passing test suite across unit, database, and web integration tests. |

## 2. Recommendations for Future Development
- **User Authentication**: Implement multi-user login sessions so multiple students can independently manage separate study plans.
- **Calendar Integration**: Export study schedules to iCalendar (`.ics`) format to sync with Google Calendar and Apple Calendar.
- **Pomodoro Timer**: Embed an active study session timer directly linked to the top-ranked task in the Study Plan.
