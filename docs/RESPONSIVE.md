# SYNTRIQ — Responsive Engineering & Breakpoint Specification (RESPONSIVE.md)

**Product**: SYNTRIQ — Think Smarter. Study Better.  
**Version**: 2.4.0 Multi-Device Layout Standard  
**Compliance**: Zero horizontal overflow, iOS auto-zoom prevention, touch target ergonomics  

---

## 1. Responsive Philosophy

SYNTRIQ adheres to a **fluid, mobile-first, content-driven layout architecture**. Rather than simply shrinking a desktop interface, the component hierarchy morphs appropriately for the physical ergonomics of each device class.

* **Mobile (320px–480px)**: One-thumb ergonomics, primary actions at touch height, wide tables converted to stacked visual cards.
* **Tablets (600px–1024px)**: Adaptive split-column grids for workload capacity and 7-day heatmaps.
* **Laptops & Desktops (1280px–1920px+)**: Multi-column priority cards with simultaneous factor ratings, quick action bars, and sticky calculation previews.

---

## 2. Tested Device & Viewport Matrix

| Category | Viewport Width | Typical Target Devices | Layout Adaptation Strategy |
|---|---|---|---|
| **Small Mobile** | `320px`–`360px` | Galaxy S8/A-series, iPhone SE 1st Gen | Single column, compact padding (12px), stacked table cards, 2-col stats grid |
| **Standard Mobile** | `375px`–`430px` | iPhone 12/13/14/15/16, Pixel 7/8, Galaxy S23/S24 | Hamburger drawer nav, full touch targets ($\ge 44\text{px}$), stacked table cards |
| **Large Mobile / Fold** | `480px`–`600px` | Surface Duo, Galaxy Z Fold (unfolded cover), Phablets | 2-column metric cards, 4-column heatmap strip |
| **Tablets (Portrait)** | `768px`–`820px` | iPad Mini, iPad 10th Gen, iPad Air | Hybrid grid, desktop navigation kicks in, full data tables with horizontal container scroll |
| **Tablets (Landscape)** | `1024px` | iPad Pro 11", Galaxy Tab S9 | Multi-column dashboard grid, 7-day heatmap full strip, side-by-side simulator |
| **Laptops / Desktops** | `1280px`–`1440px` | MacBook Pro 14", Dell XPS 13, Standard Monitors | Full 5-column overview stats grid, 4-column priority cards with subtask drawers |
| **Ultrawide & Large** | `1600px`–`1920px+` | 27"–34" QHD & 4K Ultrawide Displays | Container max-width capped at `1180px` with centered auto-margins to prevent eye strain |

---

## 3. Critical Mobile Safeguards

### 3.1 iOS Safari Auto-Zoom Shield
Browsers running iOS WebKit automatically zoom into form inputs whose computed font size is smaller than 16px.
```css
@media (max-width: 768px) {
    .form-control,
    input[type="text"],
    input[type="date"],
    select {
        font-size: 16px !important;
        min-height: 44px;
    }
}
```

### 3.2 Elimination of Horizontal Scroll
```css
html, body {
    overflow-x: hidden;
    width: 100%;
}
```

### 3.3 Dynamic Viewport Handling & Mobile Safe Area
Mobile headers and slide-over drawers use dynamic viewport height units to prevent layout collapse when browser URL bars retract:
```css
.mobile-nav-drawer {
    height: 100dvh;
    padding-bottom: env(safe-area-inset-bottom, 16px);
}
```

---

## 4. Mobile Table-to-Card Transformation Architecture

Standard data tables with 9 columns (`Task ID`, `Title`, `Subject`, `Deadline`, `Diff/Imp`, `Hours`, `Priority`, `Status`, `Actions`) cause awkward horizontal clipping on small screens. SYNTRIQ automatically transforms table rows into structured cards on screens $\le 768\text{px}$:

```css
@media (max-width: 768px) {
    .data-table thead {
        display: none;
    }
    .data-table,
    .data-table tbody,
    .data-table tbody tr,
    .data-table tbody td {
        display: block;
        width: 100%;
    }
    .data-table tbody tr {
        background: #FFFFFF;
        border: 1px solid var(--border-color);
        border-radius: var(--radius-card);
        padding: 16px;
        margin-bottom: 14px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
    }
    .data-table tbody td {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px solid #F4F3F0;
    }
    .data-table tbody td::before {
        content: attr(data-label);
        font-weight: 700;
        color: var(--text-secondary);
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
}
```

---

## 5. Playwright Viewport Verification Results
Automated headless Chromium testing verified zero horizontal overflow across 24 combinations:
* `mobile_320` (320px) &rarr; `scrollWidth: 320px` [PASS]
* `mobile_375` (375px) &rarr; `scrollWidth: 375px` [PASS]
* `mobile_414` (414px) &rarr; `scrollWidth: 414px` [PASS]
* `tablet_768` (768px) &rarr; `scrollWidth: 768px` [PASS]
* `tablet_820` (820px) &rarr; `scrollWidth: 820px` [PASS]
* `laptop_1024` (1024px) &rarr; `scrollWidth: 1024px` [PASS]
* `desktop_1440` (1440px) &rarr; `scrollWidth: 1440px` [PASS]
* `ultrawide_1920` (1920px) &rarr; `scrollWidth: 1920px` [PASS]
