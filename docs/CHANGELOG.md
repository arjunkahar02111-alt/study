# SYNTRIQ 2.0 — Release Changelog

All notable changes to the **SYNTRIQ** study planner project are documented in this file.

The project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] — 2026-11-23

### Major Release: Premium Human-Centric UI/UX, Motion System & Responsive Transformation

SYNTRIQ 2.0 represents a comprehensive architectural enhancement to visual hierarchy, motion design, mobile ergonomics, chronometry accuracy, and accessibility, while 100% preserving established brand identity, data schemas, and the core priority algorithm.

---

### Added
* **Drift-Free Chronometry Engine (`static/js/main.js`)**:
  * Implemented timestamp-anchored countdown calculation (`pomoEndTime = Date.now() + pomoTimeLeft * 1000`).
  * Integrated W3C Page Visibility API (`document.visibilitychange` listener) to guarantee 100% time accuracy across backgrounded tabs and OS sleep states.
* **Accessible Priority Legend Bar (`templates/study_plan.html`)**:
  * Multi-attribute visual legend defining High Priority ($\ge 7.0$), Moderate Priority ($4.0 - 6.9$), and Low Priority ($< 4.0$).
  * Multi-channel differentiation using colored pills, geometric badges, and star icons to satisfy WCAG 2.2 Success Criterion 1.4.1 (Use of Color).
* **Automated 16-Viewport Verification Suite (`scripts/record_baseline.py`)**:
  * End-to-end Playwright test harness testing all 16 target device screen dimensions (from 320px mobile to 1920px desktop).
  * Automated assertions for 0px horizontal overflow, slide-over drawer toggling, modal dimensions, and zero console errors.
* **Comprehensive Engineering Documentation (`docs/`)**:
  * `docs/DESIGN.md`: Visual hierarchy, color tokens, and typography specifications.
  * `docs/SKILLS.md`: Engineering skills inventory and domain requirements.
  * `docs/CREATIVITY.md`: Human-centric creative features and auditory design.
  * `docs/ANIMATIONS.md`: Micro-interactions, spring physics, and reduced-motion modes.
  * `docs/RESPONSIVE.md`: 16-viewport layout architecture and touch ergonomics.
  * `docs/ACCESSIBILITY.md`: WCAG 2.2 Level AA audit and contrast matrix.
  * `docs/TESTING.md`: Automated test methodologies and assertions.
  * `docs/IMPLEMENTATION_PLAN.md`: Phase-by-phase execution tracking.
  * `docs/RESEARCH_REFERENCES.md`: Academic, W3C, and Google web.dev research citations.
  * `docs/COMPONENT_INVENTORY.md`: Comprehensive catalog of all 21 application components.

---

### Changed
* **Focus Pomodoro Modal Geometry (`static/css/style.css`)**:
  * Rescaled SVG timer from 220px to a balanced 170px diameter.
  * Reduced modal padding to `24px 24px 18px` with compact 4px-gap ambient audio chips.
  * Total modal height reduced to $< 510\text{px}$, completely eliminating vertical scrollbars on 720px/768px laptop screens (`overflow-y: visible`).
* **Mobile Task Filter Scrolling Affordance (`static/css/style.css`)**:
  * Enabled momentum touch scrolling (`-webkit-overflow-scrolling: touch`) with CSS Scroll Snap (`scroll-snap-type: x proximity`).
  * Hidden unsightly browser scrollbars (`scrollbar-width: none; -ms-overflow-style: none;`) to prevent layout clipping of the "Upcoming" filter tab.
* **Mobile 5-Card Statistics Layout (`static/css/style.css`)**:
  * Configured `@media (max-width: 640px)` rule with `.stats-grid .stat-card:last-child { grid-column: span 2; }` so the 5th card spans both columns instead of creating an asymmetrical blank spot.
* **Human-Centric Iconography & Microcopy**:
  * Replaced raw emojis with clean SVG vector iconography across sound controls, timer buttons, stat cards, heatmap header, and capacity meter.
  * Removed culinary metaphors ("cooking", "stove", "priority recipe") in favor of natural academic language ("Focus Session", "Add Study Task", "Your study space is clear").
* **Brand Logo & Emblem Rendering**:
  * Implemented high-resolution purple-and-blue emblem (`static/images/syntriq-icon.png`) with crisp CSS rendering across desktop, drawer, and favicon.

---

### Fixed
* **Duplicated Plus Sign**: Fixed navbar and mobile drawer "Add Task" buttons where a literal `+` character was rendered alongside the plus SVG icon.
* **Background Tab Timer Throttling**: Fixed issue where Pomodoro timer would run slowly or freeze when switching to another browser tab.
* **Mobile Backdrop Click Intercept**: Fixed Playwright interaction test where backdrop click hit the open slide-over drawer on narrow screens.
* **Jinja Template Syntax Typo**: Corrected unescaped template tags in `templates/study_plan.html`.

---

### Performance & Quality Metrics
* **Total Automated Unit & Logic Tests**: 18 / 18 Passed (100%).
* **Integration & Criterion Tests**: 14 / 14 Passed (100%).
* **Viewport Responsive Tests**: 16 / 16 Viewports Passed with 0px horizontal scroll overflow.
* **Console Errors**: 0 errors across all routes.
