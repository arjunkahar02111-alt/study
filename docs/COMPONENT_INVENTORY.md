# SYNTRIQ 2.0 — Component Inventory & Design System Catalog

## 1. Catalog Overview

This document provides a comprehensive audit of all **21 interface components** comprising the SYNTRIQ 2.0 application ecosystem. Each component is documented with its template file location, DOM identifiers, visual styling, responsive adaptations, keyboard accessibility, and state transitions.

---

## 2. Component Directory

### Component 01: Application Header & Brand Navigation
* **Source**: `templates/base.html`
* **Selector**: `.app-header`, `.navbar`, `.logo-link`
* **Description**: Sticky desktop and tablet navigation bar displaying the official SYNTRIQ emblem, brand typography ("SYNTRIQ — THINK SMARTER. STUDY BETTER."), route links, sound toggle, focus timer button, and primary "Add Task" action.
* **Responsive Behavior**: On viewports $\le 768\text{px}$, route links and desktop CTA buttons collapse into a clean hamburger menu trigger (`#mobileMenuBtn`), while maintaining the brand logo and sound toggle.
* **Accessibility**: Full semantic `<header>` and `<nav role="navigation">`, keyboard focusable links with `2px solid var(--primary)` focus rings.

### Component 02: Mobile Slide-Over Navigation Drawer
* **Source**: `templates/base.html`
* **Selector**: `#mobileNavDrawer`, `#mobileDrawerOverlay`, `.drawer-close-btn`
* **Description**: Smooth slide-over modal drawer offering full-height navigation on mobile phones ($\le 768\text{px}$) with dedicated touch-sized menu items ($\ge 44\text{px}$).
* **Interactions**: Closes on backdrop tap, close button tap, route transition, or `Escape` key press. Body scroll is locked (`document.body.classList.add("nav-locked")`) while drawer is open.

### Component 03: Audio Mute & Soundscape Master Toggle
* **Source**: `templates/base.html`
* **Selector**: `#soundToggleBtn`, `#mobileSoundToggleBtn`, `.sound-toggle-btn`
* **Description**: Dual-state sound toggle button featuring clean SVG vector speaker icons (Active vs Muted).
* **State Management**: Persists sound preference across sessions in `localStorage["planner_sound_fx"]`. Controls Web Audio API procedural synthesis.

### Component 04: Focus Session Launch Button
* **Source**: `templates/base.html`
* **Selector**: `.btn-pomo-nav`
* **Description**: Distinctive secondary action pill button in the top navigation with clock SVG icon, triggering the Focus Pomodoro modal from anywhere in the application.

### Component 05: Daily Motivation & Streak Pill Banner
* **Source**: `templates/index.html`
* **Selector**: `.motivation-bar`, `.quote-content`, `.streak-pill`
* **Description**: Top greeting card presenting an inspirational quote ("Focus is the bridge between goals and accomplishment") alongside an active study streak indicator.

### Component 06: Statistics & Key Metrics 5-Grid
* **Source**: `templates/index.html`
* **Selector**: `.stats-grid`, `.stat-card`
* **Description**: Five interactive metric cards summarizing Total Tasks, Pending Tasks, Overdue Tasks, Upcoming Tasks, and Completed Tasks with animated number tickers (`animateNumberCounters`).
* **Responsive Adaptation**: On desktop: 5-column auto-fit. On mobile $\le 640\text{px}$: balanced 2-column grid with `.stat-card:last-child { grid-column: span 2; }` to eliminate awkward asymmetrical empty slots.

### Component 07: 7-Day Workload Heatmap Strip
* **Source**: `templates/index.html`
* **Selector**: `.workload-heatmap-card`, `.heatmap-strip`, `.heatmap-day-chip`
* **Description**: Interactive 7-day chronological horizon displaying daily study workload density (Empty, Light, Medium, Heavy, Overload) with color-coded badges and task counters.
* **Responsive Adaptation**: On desktop: 7 columns. On tablet: 4 columns. On small phones ($\le 520\text{px}$): 2-column mobile matrix.

### Component 08: Daily Study Capacity Meter Card
* **Source**: `templates/index.html`
* **Selector**: `.daily-capacity-card`, `.progress-bar-track`, `.progress-bar-fill`
* **Description**: Visual progress gauge comparing today's scheduled study hours against an 8-hour recommended daily capacity limit. Changes from orange gradient to crimson alert when capacity exceeds 100%.

### Component 09: Task Category Filter Tabs
* **Source**: `templates/index.html`
* **Selector**: `.tabs-header`, `.tabs-list`, `.tab-item`
* **Description**: Segmented filter navigation ("All Tasks", "Pending", "Overdue", "Upcoming", "Completed") with count badges.
* **Responsive Adaptation**: Features touch-momentum horizontal scrolling (`-webkit-overflow-scrolling: touch`), scroll snap (`scroll-snap-type: x proximity`), and hidden scrollbars to prevent clipping.

### Component 10: Responsive Adaptive Task Table / Mobile Cards
* **Source**: `templates/index.html`
* **Selector**: `.table-responsive`, `.data-table`
* **Description**: High-density tabular layout on desktop displaying Task Name, Subject, Workload Hours, Ratings, Deadline, Priority Score, and Actions.
* **Responsive Transformation**: On mobile ($\le 768\text{px}$), the table automatically reorganizes into individual touch-friendly cards via CSS pseudo-elements (`td::before { content: attr(data-label); }`).

### Component 11: Multi-Attribute Priority Badges & Status Pills
* **Source**: `templates/index.html`, `templates/study_plan.html`
* **Selector**: `.priority-pill`, `.badge`, `.badge-urgent`, `.badge-warning`, `.badge-info`
* **Description**: High-contrast semantic pills communicating task urgency and importance. Never relies on color alone: includes explicit text labels, star indicators, and icon markers.

### Component 12: Task Inline Action Button Group
* **Source**: `templates/index.html`
* **Selector**: `.actions-group`, `.btn-action`, `.btn-complete`, `.btn-edit`, `.btn-delete`
* **Description**: Precision action triggers for marking tasks complete, navigating to task editing, or deleting tasks. All targets scale to $\ge 44\text{px}$ on mobile.

### Component 13: Subtasks Real-Time Checklist Manager
* **Source**: `templates/index.html`
* **Selector**: `.subtasks-container`, `.subtasks-list`, `.subtask-item`, `.subtask-checkbox-label`
* **Description**: Expandable inline task breakdown system allowing students to decompose complex tasks into micro-steps. Features real-time completion counter, AJAX persistence, and auditory feedback.

### Component 14: Multi-Attribute Study Plan Priority Legend
* **Source**: `templates/study_plan.html`
* **Selector**: `.priority-legend-bar`, `.legend-pill`
* **Description**: Multi-attribute educational legend defining High Priority ($\ge 7.0$), Moderate Priority ($4.0 - 6.9$), and Low Priority ($< 4.0$) using distinctive geometric badges, icons, and text.

### Component 15: Ranked Priority Study Plan Cards
* **Source**: `templates/study_plan.html`
* **Selector**: `.priority-card`, `.rank-col`, `.details-col`, `.score-col`, `.actions-col`
* **Description**: Algorithmic study plan cards organized strictly by computed urgency score. Features rank badge, subject tag, difficulty and importance meters, urgency explanation, and launch focus session action.

### Component 16: Focus Pomodoro Modal
* **Source**: `templates/base.html`
* **Selector**: `#pomodoroModal`, `.modal-card`, `.pomodoro-card`
* **Description**: Compact, distraction-free study session dialog ($< 510\text{px}$ height) engineered with zero vertical scrollbars on standard 720px/768px laptop displays.

### Component 17: Circular SVG Progress Timer
* **Source**: `templates/base.html`
* **Selector**: `.timer-svg`, `#timerProgress`, `#pomoTimerText`
* **Description**: Vector SVG timer ring ($170\text{px} \times 170\text{px}$) with dynamic stroke-dashoffset animation and digital countdown readout. Driven by drift-free wall-clock timestamp synchronization.

### Component 18: Ambient Soundscape Selector Chips
* **Source**: `templates/base.html`
* **Selector**: `.ambient-sound-row`, `.ambient-chip`
* **Description**: Touch-friendly chips enabling offline-synthesized ambient audio: Rain, Café Waves, White Noise, and rhythmic Clock Ticking.

### Component 19: What-If Priority Simulator Modal
* **Source**: `templates/study_plan.html`
* **Selector**: `#simulatorModal`, `.sim-control-group`, `.sim-slider`
* **Description**: Interactive scenario planning sandbox allowing students to simulate deadline postponement (+/- days) and workload expansion (+/- hours) to preview rank impact before making schedule adjustments.

### Component 20: Keyboard Shortcuts Help Modal
* **Source**: `templates/base.html`
* **Selector**: `#keyboardModal`, `.shortcut-row`, `kbd`
* **Description**: Pro-student shortcut guide displaying keyboard commands (`N` = New Task, `D` = Dashboard, `S` = Study Plan, `P` = Pomodoro, `Space` = Start/Pause, `Esc` = Close).

### Component 21: Canvas Physics Confetti Engine
* **Source**: `templates/base.html`
* **Selector**: `#confettiCanvas`
* **Description**: Full-screen 2D canvas particle physics simulation triggering celebratory confetti burst when a student marks a task or subtask complete.
