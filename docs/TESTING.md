# SYNTRIQ — Quality Assurance & Testing Architecture (TESTING.md)

**Product**: SYNTRIQ — Think Smarter. Study Better.  
**Version**: 2.4.0 Test Suite  
**Test Frameworks**: Python `unittest`, Playwright Headless Chromium, Custom Coursework Harness  

---

## 1. Testing Philosophy & Multi-Tier Architecture

To guarantee zero regression while introducing motion and responsive enhancements, SYNTRIQ employs four complementary tiers of automated validation:

```
[Tier 1: Algorithmic Unit Tests]    -> 18 Tests in test_study_planner.py
[Tier 2: Coursework Acceptance]     -> 14 Tests in run_tests.py
[Tier 3: Playwright Browser Visual] -> 24 Responsive Viewport Tests + Interaction
[Tier 4: HTTP Route Regression]     -> Test Client Status Codes (200 OK)
```

---

## 2. Test Suites Detailed

### 2.1 Tier 1: Algorithmic Unit Tests (`test_study_planner.py`)
Validates core mathematical and database operations:
1. `test_calculate_priority_standard`: Base formula output check ($0.4U + 0.3I + 0.2D + 0.1W$).
2. `test_urgency_weights`: Urgency scores for overdue, today, 3 days, 7 days, 14 days, and distant deadlines.
3. `test_workload_weights`: Workload weights for estimated hours ($<1\text{h}$, $1\text{h}$–$2\text{h}$, $2\text{h}$–$4\text{h}$, $4\text{h}$–$6\text{h}$, $\ge 6\text{h}$).
4. `test_priority_categories`: High ($\ge 4.0$), Moderate ($3.0$–$3.9$), Low ($<3.0$).
5. `test_database_crud`: Task insertion, retrieval, update, and deletion in SQLite.
6. `test_mark_completed`: Updating task status from `Pending` to `Completed`.
7. `test_subtasks_lifecycle`: Creation, toggle completion, and deletion of task sub-milestones.
8. `test_calendar_export`: iCal (.ics) format validation.

**Execution Command**:
```powershell
python -m unittest test_study_planner.py
```
*Status: 18 / 18 Passed in 0.912s.*

---

### 2.2 Tier 2: Coursework Acceptance Tests (`run_tests.py`)
Validates all 14 Criterion B / Criterion D requirements:
* Test 1: Add task with valid inputs &rarr; PASSED
* Test 2: Add task with empty title &rarr; PASSED
* Test 3: Add task with invalid date &rarr; PASSED
* Test 4: Task priority calculation &rarr; PASSED
* Test 5: Dynamic priority updates &rarr; PASSED
* Test 6: Database task retrieval &rarr; PASSED
* Test 7: Task editing & recalculation &rarr; PASSED
* Test 8: Task deletion &rarr; PASSED
* Test 9: Marking tasks as completed &rarr; PASSED
* Test 10: Overdue task detection & display &rarr; PASSED
* Test 11: Upcoming deadline detection & display &rarr; PASSED
* Test 12: Data persistence across refreshes &rarr; PASSED
* Test 13: Algorithmic study plan generation & sorting &rarr; PASSED
* Test 14: User interface navigation and integrity &rarr; PASSED

**Execution Command**:
```powershell
python run_tests.py
```
*Status: 14 / 14 Passed (100%).*

---

### 2.3 Tier 3: Playwright Headless Visual & Responsive Audit (`scripts/record_baseline.py`)
Tests 8 physical device viewports across all core routes:
* Viewports: `320px`, `375px`, `414px`, `768px`, `820px`, `1024px`, `1440px`, `1920px`.
* Evaluates:
  - Horizontal overflow (`document.documentElement.scrollWidth > window.innerWidth`).
  - Mobile menu button toggle and slide-over drawer animation.
  - Pomodoro focus modal visibility and backdrop blur.
  - Console error tracking (`page.on("console")`).

**Execution Command**:
```powershell
python scripts/record_baseline.py
```
*Status: Zero horizontal overflow across all tested viewports. Zero console errors.*

---

### 2.4 Tier 4: Flask Test Client Route Verification
Probes live application endpoints without requiring external network connectivity:
* `GET /` &rarr; `200 OK`
* `GET /dashboard` &rarr; `200 OK`
* `GET /study-plan` &rarr; `200 OK`
* `GET /add-task` &rarr; `200 OK`
* `GET /export/calendar.ics` &rarr; `200 OK`
* `GET /static/css/style.css` &rarr; `200 OK`
* `GET /static/js/main.js` &rarr; `200 OK`

---

## 3. Regression Prevention Checklist
Before deploying any code modification:
1. [ ] Run `python -m unittest test_study_planner.py`
2. [ ] Run `python run_tests.py`
3. [ ] Confirm zero horizontal scroll on mobile viewport ($320\text{px}$)
4. [ ] Verify touch targets are $\ge 44\text{px}$
5. [ ] Verify sound effects remain opt-in and can be muted
6. [ ] Confirm `git status` reflects only intended file modifications
