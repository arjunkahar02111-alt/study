# SYNTRIQ — Master Visual Design System Specification (DESIGN.md)

**Product Name**: SYNTRIQ — Think Smarter. Study Better.  
**Version**: 2.4.0 (Production Motion & Responsive Release)  
**Architect**: Principal Frontend Architect & Senior Product Designer  
**Status**: Active Master Specification  

---

## 1. Brand Identity & Creative Metaphor

SYNTRIQ blends high-performance academic computing with the vibrant, tactile energy of a modern culinary studio ("Deep Work Kitchen"). Study tasks are treated as ingredients prepared with precision, prioritizing mental energy and time management through algorithmic scoring.

* **Primary Persona**: University, High School, and Pre-College students managing multi-subject workloads with competing deadlines.
* **Core Brand Colors**: High-contrast Orange (`#FF6B00`) representing mental energy and focus, contrasted against deep Obsidian Black (`#000000`) and soft Warm White Canvas (`#FAF9F7`).

---

## 2. Token Architecture

Tokens are categorized into three structured layers: **Primitive**, **Semantic**, and **Component**.

```
[Primitive Tokens] -> [Semantic Tokens] -> [Component Tokens]
 (Raw Hex / Sizes)    (Role / Intent)     (Specific Elements)
```

### 2.1 Primitive Tokens

```css
/* Color Palette Primitives */
--color-orange-500: #FF6B00;
--color-orange-600: #E05E00;
--color-orange-100: #FFF0E6;
--color-orange-50:  #FFF8F3;

--color-neutral-900: #111111;
--color-neutral-800: #1F1F1F;
--color-neutral-600: #666666;
--color-neutral-400: #888888;
--color-neutral-200: #ECEAE6;
--color-neutral-100: #FAF9F7;
--color-neutral-0:   #FFFFFF;

--color-emerald-500: #10B981;
--color-emerald-100: #ECFDF5;

--color-rose-500:    #EF4444;
--color-rose-100:    #FEF2F2;

--color-amber-500:   #F59E0B;
--color-amber-100:   #FFFBEB;

--color-blue-500:    #3B82F6;
--color-blue-100:    #EFF6FF;

/* Typography Primitives */
--font-heading: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
--font-body:    'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
--font-mono:    'JetBrains Mono', monospace;
```

### 2.2 Semantic Tokens

```css
:root {
    /* Brand Semantics */
    --primary:         var(--color-orange-500);
    --primary-hover:   var(--color-orange-600);
    --primary-light:   var(--color-orange-100);
    --primary-subtle:  var(--color-orange-50);
    
    --secondary:       #000000;
    --secondary-hover: var(--color-neutral-800);
    --secondary-light: #F4F4F4;

    --bg-page:         var(--color-neutral-100);
    --bg-card:         var(--color-neutral-0);
    
    --text-primary:    var(--color-neutral-900);
    --text-secondary:  var(--color-neutral-600);
    --text-muted:      var(--color-neutral-400);
    
    /* Functional Status */
    --success:         var(--color-emerald-500);
    --success-light:   var(--color-emerald-100);
    --danger:          var(--color-rose-500);
    --danger-light:    var(--color-rose-100);
    --warning:         var(--color-amber-500);
    --warning-light:   var(--color-amber-100);
    --info:            var(--color-blue-500);
    --info-light:      var(--color-blue-100);

    /* Spacing Units */
    --spacing-xs: 4px;
    --spacing-sm: 8px;
    --spacing-md: 16px;
    --spacing-lg: 24px;
    --spacing-xl: 32px;

    /* Border Radius */
    --radius-btn:  12px;
    --radius-card: 16px;
    --radius-sm:   8px;
    --radius-full: 9999px;

    /* Elevation & Shadows */
    --shadow-soft:  0 4px 20px rgba(0, 0, 0, 0.04), 0 1px 3px rgba(0, 0, 0, 0.02);
    --shadow-hover: 0 12px 32px rgba(255, 107, 0, 0.12), 0 4px 12px rgba(0, 0, 0, 0.04);
    --shadow-card:  0 6px 24px rgba(0, 0, 0, 0.05);
    --border-color: var(--color-neutral-200);

    /* Z-Index Stacking Context Layers */
    --z-base:       0;
    --z-dropdown:   50;
    --z-sticky-nav: 100;
    --z-toggle:     101;
    --z-helper:     90;
    --z-overlay:    998;
    --z-modal:      999;
    --z-confetti:   9999;
}
```

---

## 3. Typography Hierarchy

| Level | Font Family | Size (Desktop) | Size (Mobile) | Weight | Line Height | Tracking |
|---|---|---|---|---|---|---|
| **H1 Hero** | Plus Jakarta Sans | `2.1rem` (33.6px) | `clamp(1.4rem, 5vw, 1.8rem)` | 800 | 1.20 | `-0.025em` |
| **H2 Section** | Plus Jakarta Sans | `1.5rem` (24px) | `1.3rem` (20.8px) | 800 | 1.25 | `-0.02em` |
| **H3 Card** | Plus Jakarta Sans | `1.15rem` (18.4px) | `1.05rem` (16.8px) | 700 | 1.30 | `-0.015em` |
| **Body Large** | Inter | `1.0rem` (16px) | `0.95rem` (15.2px) | 500 | 1.60 | `normal` |
| **Body Regular** | Inter | `0.92rem` (14.7px) | `0.88rem` (14px) | 400 | 1.55 | `normal` |
| **Caption/Label** | Plus Jakarta Sans | `0.78rem` (12.5px) | `0.75rem` (12px) | 700 | 1.30 | `+0.05em` |
| **Numeric/Math** | JetBrains Mono | `1.35rem`–`4.0rem` | `1.15rem`–`2.8rem` | 800 | 1.00 | `normal` |

---

## 4. Component Visual Standards

### 4.1 Buttons
* **Primary**: Orange background (`#FF6B00`), white text, 12px radius, min-height 44px on mobile. Hover: lifts 2px with soft orange shadow glow (`rgba(255, 107, 0, 0.35)`). Active: scales down to `0.97` for tactile click feel.
* **Secondary**: Obsidian black (`#000000`), white text, 12px radius.
* **Outline**: Transparent background, 1.5px border (`var(--border-color)`), text primary.
* **Action Icon Buttons**: Minimum dimensions $44 \times 44\text{px}$ on touch screens, 8px radius.

### 4.2 Cards
* **White Surface**: 16px radius, 1px solid border (`var(--border-color)`), soft shadow (`--shadow-card`).
* **Top Priority Card**: Highlighted with an active ambient orange glow pulse (`@keyframes syntriqPriorityPulse`) and a left orange indicator accent.

### 4.3 Form Inputs
* **Dimensions**: 12px border-radius, minimum 44px height on touch devices.
* **Mobile Zoom Prevention**: Explicitly set to `16px` on mobile viewports ($\le 768\text{px}$) to prevent iOS Safari auto-zoom.
* **Focus State**: 2px solid orange border with `box-shadow: 0 0 0 4px rgba(255, 107, 0, 0.15)`.

---

## 5. Visual Regression & Brand Protection Checklist
* [x] Never replace `#FF6B00` or `#000000` with unapproved color variations.
* [x] Never introduce layout-triggering animations (`top`, `left`, `margin`, `width`).
* [x] Maintain high contrast ratios ($\ge 4.5:1$ for normal text, $\ge 3:1$ for large headings and UI controls).
* [x] Ensure that mobile views stack cleanly without table truncation or horizontal window scrolling.
