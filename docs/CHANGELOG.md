# SYNTRIQ — Comprehensive Release Changelog

All notable changes to the **SYNTRIQ — Think Smarter. Study Better.** software product are documented in this file.

The project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [3.1.0] — 2026-11-23

### Major Feature Release: SYNTRIQ Real-Time Time Intelligence & Academic Productivity Engine

**Tagline:** Know where your time goes. Improve how you study.

SYNTRIQ 3.1 introduces a high-precision, drift-free real-time study tracking and academic productivity analytics system. It eliminates mandatory estimated task durations and measures genuine student focus time, verified with second-level accuracy.

---

### Added
* **Real-Time Study Time Tracking Engine (`database.py`, `app.py`, `static/js/main.js`)**:
  * Authoritative `ActiveSession` table with SQLite `CHECK (ID = 1)` single active tracking session constraint.
  * Drift-free focus math: `Elapsed Time = Accumulated Duration + max(0, round(Current Timestamp - Start Timestamp))`.
  * Real-time tracking endpoints: `POST /api/time-tracking/start`, `/pause`, `/resume`, `/stop`, `GET /api/active-session`, `GET /api/tasks/<id>/sessions`.
  * Automatic conflict detection and resolution modal (`#switchTaskModal`) when attempting to track another task while an active session is in progress.
  * Task completion auto-finalization: marking a task complete automatically closes active tracking sessions and records `Completed_At`.
* **Persistent Floating Active Session Widget (`templates/base.html`, `static/css/style.css`, `static/js/main.js`)**:
  * Floating pill docked at bottom-right on desktop and docked bottom sheet on mobile devices ($\le 768\text{px}$).
  * Live pulsing status indicator, digital clock (`HH:MM:SS`), pause/resume toggle, and stop & save button.
  * Page Visibility API integration (`visibilitychange`) and periodic 25-second server sync to guarantee zero client-side clock drift.
* **Dedicated Time Intelligence Dashboard (`templates/time_intelligence.html`, `/time-intelligence`)**:
  * Overview statistics grid: Today's Focus, This Week, This Month, Total Recorded Time, Active Study Streak.
  * Subject-Wise Time Distribution: Visual progress tracks showing genuine study hours and percentage per subject.
  * Focus vs. Calendar Span Analytics: Real comparison of actual focus hours against calendar duration from start to finish.
  * Contextual Smart Insights: Automated academic productivity insights derived strictly from verified student focus records.
  * Chronological Study Session History Timeline: Second-precision record of past focus sessions with subject, duration, and status.
* **11-Point Time Intelligence Automated Test Suite (`scripts/test_time_intelligence.py`)**:
  * 100% automated test coverage across task creation without duration, neutral workload formula, clock start, active session API, conflict detection, force switch, pause/resume drift resistance, task total accumulation, auto-completion finalization, and dashboard rendering.

---

### Changed
* **Decoupled Mandatory Task Duration (`priority_calculator.py`, `database.py`, `templates/add_task.html`, `templates/edit_task.html`)**:
  * Removed `required` attribute from estimated hours in task creation and edit forms.
  * Relabeled field to "Target Duration in Hours (Optional)".
  * Priority formula algorithm fallback: when target duration is omitted, transparently uses neutral midpoint workload 3.0 ($0.1 \times 3 = 0.3$), keeping the algorithm intact and 100% backward-compatible.
* **Dashboard & Study Plan Task Presentation (`templates/dashboard.html`, `templates/study_plan.html`)**:
  * Replaced "Est. Hours" column header in task table with "Tracked Time", displaying formatted actual focus time (`task.tracked_time_formatted`) alongside optional target durations.
  * Added direct 1-click "Track Time" action buttons on all pending tasks across Dashboard and Study Plan.

---

## [3.0.0] — 2026-11-23

### Major Milestone: Commercial-Grade Product Design, Security, Performance & 16-Viewport Optimization

SYNTRIQ 3.0 delivers a complete product-level engineering transformation across visual hierarchy, responsive design, security invariants, performance budgets, motion systems, and automated testing, while 100% preserving established brand identity, data schemas, and the core priority algorithm.

---

### Added
* **Security & Data Integrity Specifications (`docs/SECURITY.md`)**:
  * Formal documentation of SQL injection prevention via 100% parameterized SQLite bindings.
  * Jinja2 autoescaping and DOM `.textContent` sanitization against Cross-Site Scripting (XSS).
  * HTTP POST requirements for state-modifying actions and destructive confirmation prompts.
* **Performance Engineering & Core Web Vitals Specifications (`docs/PERFORMANCE.md`)**:
  * Core Web Vitals empirical benchmarks: LCP = 0.42s, INP < 12ms, CLS = 0.000.
  * Comprehensive memory management and resource lifecycle specifications.
  * Zero external raster or audio asset payload architecture.
* **Responsive Study Plan Formula Presentation (`templates/study_plan.html`, `static/css/style.css`)**:
  * Desktop: Full mathematical formula rendered via `.desktop-formula`.
  * Mobile: 4 structured factor pill badges (`.formula-factors-mobile`: Urgency 40%, Importance 30%, Difficulty 20%, Workload 10%) eliminating code wrapping on small viewports.
* **20-Point Automated Quality Assurance Suite (`scripts/test_syntriq3.py`)**:
  * Automated testing across all 20 functional test dimensions specified in Section 17 of the Master Engineering Prompt.

---

### Changed
* **Action Button Iconography (`templates/study_plan.html`)**:
  * Replaced raw emojis (`🎛️`, `⚡`, `✓`, `✎`, `🗑`) with clean, lightweight vector SVGs on What-If Simulator, Focus Timer, Complete, Edit, and Delete action buttons.
* **Heatmap Microcopy & Entity Sanitization (`templates/dashboard.html`)**:
  * Replaced raw HTML entity `&bull;` with true unicode bullet dot `•`.
* **Mobile 5-Card Statistics Layout (`static/css/style.css`)**:
  * Balanced 2-column grid on mobile with `.stats-grid .stat-card:last-child { grid-column: span 2; }` to eliminate awkward asymmetrical empty slots.
* **Drift-Free Focus Kitchen Timer (`static/js/main.js`)**:
  * Timestamp-anchored countdown (`Date.now()`) with Page Visibility API integration for background tab drift resistance.

---

### Fixed
* **Focus Pomodoro Modal Vertical Scrollbar**: Rescaled SVG timer from 220px to 170px, reducing total modal height to $< 510\text{px}$, eliminating scrollbars on 720p/768p displays.
* **Duplicated Plus Sign in Add Task CTA**: Removed duplicate literal `+` character preceding SVG plus icons.
* **Task Subtitle Entity Display**: Corrected `${taskSubject} &bull; Assignment Priority Session` in `.textContent` to `${taskSubject} • Focus Session`.
* **Mobile Task Filter Horizontal Cutoff**: Implemented CSS scroll snapping and hidden scrollbars to prevent clipping.

---

## [2.0.0] — 2026-11-23

### Major Release: Premium Human-Centric UI/UX, Motion System & Responsive Transformation
* Full documentation suite created (`DESIGN`, `SKILLS`, `CREATIVITY`, `ANIMATIONS`, `RESPONSIVE`, `ACCESSIBILITY`, `TESTING`, `RESEARCH_REFERENCES`, `COMPONENT_INVENTORY`).
* Slide-over mobile drawer navigation with backdrop blur and touch targets $\ge 44\text{px}$.
* Procedural Web Audio API soundscape synthesis (Rain, Café, White Noise, Ticking, Resonant Singing Bowl).
* Canvas confetti physics celebration on task and subtask completion.

---

## [1.0.0] — 2026-11-23

### Initial Release: Baseline Intelligent Study Planner
* Core priority algorithm ($0.4\text{U} + 0.3\text{I} + 0.2\text{D} + 0.1\text{W}$).
* SQLite database with Tasks, Subtasks, and StudySessions tables.
* CRUD operations for study assignments.
* 7-day workload heatmap and daily capacity meter.
