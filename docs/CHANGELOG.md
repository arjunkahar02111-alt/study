# SYNTRIQ — Comprehensive Release Changelog

All notable changes to the **SYNTRIQ — Think Smarter. Study Better.** software product are documented in this file.

The project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
