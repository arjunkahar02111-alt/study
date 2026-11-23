# SYNTRIQ — Motion Design & Animation Specification (ANIMATIONS.md)

**Product**: SYNTRIQ — Think Smarter. Study Better.  
**Version**: 2.4.0 Motion System  
**Engine**: CSS3 Transitions, Keyframes & requestAnimationFrame  
**Compliance**: WCAG 2.2 SC 2.3.3 Animation from Interactions & prefers-reduced-motion  

---

## 1. Motion Principles

1. **Purposeful & Informative**: Every animation communicates state change, hierarchy, or spatial orientation. No decorative or gratuitous movement.
2. **Compositor-Only Execution**: Restrict motion strictly to `transform` and `opacity` properties to bypass browser layout reflows and paint cycles.
3. **Natural Physics & Deceleration**: Elements enter with rapid acceleration and smooth deceleration (`cubic-bezier(0.16, 1, 0.3, 1)`), mimicking real-world friction.
4. **Predictable & Non-Blocking**: Interactive controls remain clickable throughout transitions; animations never hold up user workflows.

---

## 2. Standardized Timing Tokens

```css
:root {
    /* Timing Tokens */
    --duration-instant:   80ms;
    --duration-micro:     150ms;
    --duration-button:    180ms;
    --duration-modal:     280ms;
    --duration-card:      420ms;
    --duration-progress:  800ms;

    /* Physics Easing Curves */
    --ease-out-expo:   cubic-bezier(0.16, 1, 0.3, 1);   /* Smooth deceleration */
    --ease-in-out:      cubic-bezier(0.4, 0, 0.2, 1);    /* Standard transition */
    --ease-spring:      cubic-bezier(0.34, 1.3, 0.64, 1); /* Tactile bounce */
}
```

---

## 3. Core Keyframe Library

### 3.1 Component Entrance (`syntriqFadeInUp`)
```css
@keyframes syntriqFadeInUp {
    from {
        opacity: 0;
        transform: translateY(16px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
```

### 3.2 Modal Scale-Up (`syntriqScaleUp`)
```css
@keyframes syntriqScaleUp {
    from {
        opacity: 0;
        transform: scale(0.95) translateY(8px);
    }
    to {
        opacity: 1;
        transform: scale(1) translateY(0);
    }
}
```

### 3.3 Top Priority Aura Pulse (`syntriqPriorityPulse`)
```css
@keyframes syntriqPriorityPulse {
    0%, 100% {
        box-shadow: 0 6px 24px rgba(255, 107, 0, 0.16), 0 2px 6px rgba(0, 0, 0, 0.04);
        border-color: var(--primary);
    }
    50% {
        box-shadow: 0 12px 36px rgba(255, 107, 0, 0.34), 0 4px 12px rgba(255, 107, 0, 0.18);
        border-color: var(--primary-hover);
    }
}
```

---

## 4. Staggered Orchestration

Lists and card grids stagger their entrance using dynamic CSS variables:

```css
.stats-grid .stat-card {
    animation: syntriqFadeInUp 0.42s var(--ease-out-expo) both;
    animation-delay: calc(var(--stagger, 0) * 55ms);
}

.priority-list .priority-card {
    animation: syntriqFadeInUp 0.45s var(--ease-out-expo) both;
    animation-delay: calc(var(--stagger, 0) * 50ms);
}

.data-table tbody tr {
    animation: syntriqFadeInUp 0.38s var(--ease-out-expo) both;
    animation-delay: calc(var(--stagger, 0) * 35ms);
}
```

---

## 5. Micro-Interaction Hover & Click Feedback

* **Buttons**:
  ```css
  .btn {
      transition: transform 0.18s var(--ease-out-expo),
                  box-shadow 0.18s ease,
                  background-color 0.18s ease;
  }
  .btn:hover {
      transform: translateY(-2px);
  }
  .btn:active {
      transform: scale(0.97) translateY(1px);
  }
  ```
* **Stat Cards**:
  ```css
  .stat-card:hover {
      transform: translateY(-3px);
      box-shadow: 0 10px 28px rgba(0, 0, 0, 0.08);
  }
  ```

---

## 6. Accessibility & Reduced Motion

When a student or system has enabled `prefers-reduced-motion: reduce`, all non-essential movement is disabled immediately:

```css
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.001ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.001ms !important;
        scroll-behavior: auto !important;
    }
    .card-top-priority {
        animation: none !important;
    }
}
```
* **Number Counter Fallback**: The JavaScript counter animation inspects `window.matchMedia("(prefers-reduced-motion: reduce)")` and instantly sets the final number without running the timer loop.
