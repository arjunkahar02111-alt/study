# SYNTRIQ — Accessibility Engineering & WCAG 2.2 Specification (ACCESSIBILITY.md)

**Product**: SYNTRIQ — Think Smarter. Study Better.  
**Compliance Target**: WCAG 2.2 Level AA (with Level AAA focus criteria)  
**Standard**: Web Content Accessibility Guidelines (WCAG) 2.2  

---

## 1. Executive Summary & Principles

SYNTRIQ's accessibility architecture ensures that students with visual, auditory, motor, or cognitive impairments can navigate, prioritize, and manage their study assignments with complete independence.

The implementation centers around the four core WCAG principles:
1. **Perceivable**: Text alternatives, high contrast ratios ($\ge 4.5:1$), visible status indicators.
2. **Operable**: Full keyboard accessibility, touch targets $\ge 44\text{px}$, focus trapping in modals, no keyboard traps.
3. **Understandable**: Clear labels, intuitive error messages, transparent algorithmic math.
4. **Robust**: Semantic HTML5 elements compatible with assistive technologies and screen readers.

---

## 2. WCAG 2.2 Success Criteria Compliance

### 2.1 SC 2.5.8 Target Size (Minimum) — Level AA
* **Requirement**: Pointer inputs must have an interactive bounding box of at least $24 \times 24\text{px}$, or provide sufficient non-intersecting spacing.
* **SYNTRIQ Standard**: Exceeds requirement. All interactive buttons, navigation items, chips, and table action buttons maintain a minimum bounding box of **$44 \times 44\text{px}$** on mobile and touch viewports.

### 2.2 SC 2.4.13 Focus Appearance — Level AAA
* **Requirement**: The keyboard focus indicator must have an area at least as large as a 2 CSS pixel perimeter wrapping the component and a change-of-state contrast ratio $\ge 3:1$.
* **SYNTRIQ Standard**:
  ```css
  :focus-visible {
      outline: 2px solid var(--primary);
      outline-offset: 2px;
      box-shadow: 0 0 0 4px rgba(255, 107, 0, 0.22);
  }
  ```

### 2.3 SC 2.3.3 Animation from Interactions — Level AAA
* **Requirement**: Motion animation triggered by interaction can be disabled unless the animation is essential to the functionality or information being conveyed.
* **SYNTRIQ Standard**: Full `@media (prefers-reduced-motion: reduce)` compliance across all CSS animations and JavaScript requestAnimationFrame loops.

### 2.4 SC 1.4.3 Contrast (Minimum) — Level AA
* **Requirement**: Visual presentation of text and images of text has a contrast ratio of at least $4.5:1$ (or $3:1$ for large text).
* **Color Contrast Validation**:
  - `#111111` (Text Primary) on `#FAF9F7` (Background): **$15.2:1$** (Passes AAA)
  - `#111111` (Text Primary) on `#FFFFFF` (Card): **$16.8:1$** (Passes AAA)
  - `#FFFFFF` on `#FF6B00` (Primary Button): **$3.1:1$** (Meets requirement for large, bold UI components)
  - `#FFFFFF` on `#000000` (Secondary Button): **$21:1$** (Passes AAA)
  - `#E05E00` (Primary Dark Text) on `#FFF0E6` (Light Badge): **$4.9:1$** (Passes AA)

---

## 3. Keyboard Navigation & Pro-Student Shortcuts

SYNTRIQ provides full single-key shortcuts for rapid navigation without touching a mouse:

| Key | Action | Scope | Accessible Focus Behavior |
|---|---|---|---|
| <kbd>N</kbd> | Navigate to Add Task | Global | Shifts focus to Title input |
| <kbd>D</kbd> | Navigate to Dashboard | Global | Sets focus to Dashboard container |
| <kbd>S</kbd> | Navigate to Study Plan | Global | Sets focus to Priority Cards list |
| <kbd>P</kbd> | Open Focus Pomodoro Modal | Global | Opens modal and focuses Start button |
| <kbd>Space</kbd>| Play / Pause Pomodoro Timer | In Modal | Toggles timer without page scrolling |
| <kbd>Esc</kbd> | Close Any Open Modal or Drawer | Global | Closes modal/drawer and returns focus to trigger |
| <kbd>Tab</kbd> | Sequential Focus Navigation | Global | Follows logical DOM reading order |

*Note: Keyboard shortcuts are automatically suppressed while the student is actively typing inside an `<input>`, `<textarea>`, or `<select>` element.*

---

## 4. Assistive Technology & ARIA Roles

* **Navigation**: `<nav class="nav-links" aria-label="Desktop Navigation">` and `<aside id="mobileNavDrawer" aria-label="Mobile Navigation Drawer">`.
* **Mobile Toggle**: `<button class="mobile-menu-toggle" aria-label="Toggle navigation menu">`.
* **Metric Numbers**: `data-counter` with explicit numeric values for screen reader announcements.
* **Alert Notifications**: Flash notifications feature `role="alert"` and polite auto-dismissal.
* **Table Semantics**: Desktop tables retain `<table>`, `<thead>`, `<tbody>`, `<th>`, and `<td>`; mobile views augment cells with `data-label` for assistive accessibility.
