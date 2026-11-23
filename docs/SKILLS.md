# SYNTRIQ — AI Agent Operating Instructions (SKILLS.md)

**Target Product**: SYNTRIQ — Think Smarter. Study Better.  
**Stack**: Python 3.13 / Flask / SQLite3 / Vanilla ES6+ Web Audio & Canvas / Modern CSS3  
**Audience**: AI Coding Agents, Engineers, and Automated Contributors  

---

## 1. Prime Directive: Controlled Enhancement, Zero Regression

Every agent operating on the SYNTRIQ repository must strictly adhere to the following workflow:

```
[1. INSPECT] -> [2. PLAN] -> [3. IMPLEMENT] -> [4. TEST] -> [5. VERIFY] -> [6. REPORT]
```

### Non-Negotiable Boundaries:
1. **Never Redesign from Scratch**: Preserve existing user workflows, templates, and UI conventions.
2. **Never Break Backend Routes or DB Schema**: SQLite table `tasks` with columns `Task_ID`, `Task_Title`, `Task_Subject`, `Task_Deadline`, `Task_Difficulty`, `Task_Importance`, `Estimated_Hours`, `Priority_Score`, `Task_Status`, `Created_At`.
3. **Preserve Priority Algorithm**: $0.4 \times \text{Urgency} + 0.3 \times \text{Importance} + 0.2 \times \text{Difficulty} + 0.1 \times \text{Workload}$.
4. **Never Leave Broken Layouts**: Every change must maintain zero horizontal overflow across 320px–1920px viewports.
5. **No Heavy Framework Overhead**: Do not introduce React, Vue, jQuery, or bloated CSS frameworks. Pure vanilla JS and clean CSS provide 60 FPS performance and offline reliability.

---

## 2. Directory Architecture & Naming Conventions

```
E:\Aasu\
├── app.py                      # Flask web server, route controllers, session handling
├── database.py                 # SQLite DAO methods (create, read, update, delete, subtasks)
├── priority_calculator.py      # Algorithmic priority score computation & category mapper
├── test_study_planner.py       # 18 Unit tests covering all algorithmic edge cases
├── run_tests.py                # 14 Acceptance tests for Criterion B/D coursework compliance
├── docs/                       # Project documentation system
│   ├── DESIGN.md               # Master visual design specification & token system
│   ├── SKILLS.md               # Operating instructions for future AI agents
│   ├── CREATIVITY.md           # Creative experience, audio, and micro-interaction guide
│   ├── ANIMATIONS.md           # Motion design specification & timing tokens
│   ├── RESPONSIVE.md           # Multi-device responsive engineering guide
│   ├── ACCESSIBILITY.md        # WCAG 2.2 Level AA/AAA compliance specifications
│   ├── TESTING.md              # Quality assurance, automated tests, & Playwright
│   └── IMPLEMENTATION_PLAN.md  # Audit findings, phased plan, and status tracking
├── scripts/
│   └── record_baseline.py      # Playwright multi-viewport headless visual audit runner
├── static/
│   ├── css/
│   │   └── style.css           # Modern CSS3 with tokens, motion keyframes, & mobile cards
│   ├── js/
│   │   └── main.js             # ES6+ UI controller, Pomodoro, Web Audio, Canvas confetti
│   ├── images/                 # Optimized brand assets (syntriq-icon, apple-touch-icon)
│   └── favicon.ico             # Extracted multi-resolution favicon
└── templates/
    ├── base.html               # Shared layout, header, drawer, Pomodoro modal, audio
    ├── dashboard.html          # Stats cards, weekly heatmap, workload capacity, table
    ├── study_plan.html         # Priority card list, subtask checklist, What-If simulator
    ├── add_task.html           # Task input form with dynamic priority score preview
    └── edit_task.html          # Task modification form with recalculation
```

---

## 3. Engineering Workflows & Test Commands

Before marking any turn or task complete, run the verification commands:

```powershell
# 1. Run Unit Test Suite (18 tests)
python -m unittest test_study_planner.py

# 2. Run Coursework Acceptance Tests (14 tests)
python run_tests.py

# 3. Verify Route Responses & Health
python -c "from app import app; c = app.test_client(); [print(r, c.get(r).status_code) for r in ['/', '/dashboard', '/study-plan', '/add-task']]"

# 4. Run Automated Playwright Viewport Audit (320px to 1920px)
python scripts/record_baseline.py
```

---

## 4. Safe Coding Rules
* **Compositor-Only Animations**: Restrict CSS transitions to `transform` and `opacity`. Never animate `top`, `left`, `margin`, or `height`.
* **Mobile First**: Design components to adapt dynamically down to 320px. Ensure interactive touch targets are $\ge 44\text{px}$.
* **Accessible Inputs**: Always set `font-size: 16px` on mobile inputs to prevent iOS auto-zoom.
* **Respect Motion Preferences**: Wrap all continuous or large motion in `@media (prefers-reduced-motion: reduce)`.
* **Safe Stacking Contexts**: Refer to the z-index tokens in `docs/DESIGN.md`. Never use arbitrary values like `z-index: 999999`.
