# Mastery Pulse — Frontend UI/UX Audit & Improvement PRD
**Iteration:** 1 | **Delivery intent:** Prod (exhaustive) | **Date:** 2026-08-31

---

## Problem Statement

The Mastery Pulse frontend is a React 18 + TypeScript SPA targeting Deloitte practitioners and admins. A complete audit was conducted against Deloitte enterprise UI/UX best practices across seven dimensions: accessibility (WCAG 2.1 AA), design consistency, responsive design, performance, information architecture, interaction patterns, and component/i18n readiness. The audit surfaces what is already well-implemented and what requires remediation, and produces a prioritized improvement plan.

---

## Executive Summary

The frontend demonstrates **strong foundational architecture** — CSS design tokens, dark mode support, TanStack Query server-state pattern, HttpOnly cookie auth, and semantic HTML are all correctly implemented. However, across the seven audit dimensions, **five of six enterprise compliance gates fail**, with accessibility being the most critical. The improvements are organized into three tiers by impact and effort.

---

## Audit Findings: What Already Aligns ✅

| Dimension | Finding | Evidence |
|---|---|---|
| **Design Consistency** | CSS custom property design token system with full light + dark mode | `index.css:17–99` |
| **Design Consistency** | Dark mode via `prefers-color-scheme` + `[data-theme]` explicit toggle (correct dual-block pattern) | `index.css:51–99` |
| **Accessibility** | Semantic HTML: `<nav>`, `<main>`, `<h1>`–`<h3>`, `<button type="...">`, `<form onSubmit>` | `App.tsx:71`, `PortalLayout.tsx:77` |
| **Accessibility** | Admin toggle checkbox is inside its `<label>` — correct association | `LoginPage.tsx:172–191` |
| **Interaction Patterns** | Loading spinner, empty state, error message CSS classes exist globally | `index.css:229–239` |
| **Interaction Patterns** | TanStack Query manages all server state — no raw fetch in components | `hooks/index.ts` |
| **Security / Data** | Zero `localStorage`/`sessionStorage` usage — all state server-side | `SessionContext.tsx`, CLAUDE.md |
| **Interaction Patterns** | Proper disabled states on all buttons during loading | `LoginPage.tsx:338`, `QuizRunner.tsx:446` |
| **Accessibility** | `autoComplete` attributes on inputs (email, name, current-password) | `LoginPage.tsx:229, 269, 357` |
| **Performance** | TanStack Query with 5-min staleTime + bounded 5s polling for pending paths | `main.tsx:9`, `QuizRunner.tsx:763` |

---

## Audit Findings: Gaps & Violations ❌

### Tier 1 — Critical (WCAG 2.1 AA violations, enterprise policy)

#### A1 · Accessibility — Form Label Binding Missing
**Slug:** `a11y-form-label-binding` | **File:** `LoginPage.tsx:213–295`

All inputs in `LoginPage` use a visual `labelStyle` positioned above each input, but **no `id`/`htmlFor` binding** exists. Screen readers cannot associate the label text with the input field. This violates WCAG 2.1 SC 1.3.1 (Info and Relationships) and SC 2.4.6 (Headings and Labels).

**Fix:** Add `id="field-email"` etc. to each input; add `htmlFor="field-email"` to each label. Add `aria-describedby="error-message"` pointing at the error `<p>` when validation fails.

```tsx
// Before
<label style={labelStyle}>Work email *</label>
<input type="email" ... />

// After
<label htmlFor="field-email" style={labelStyle}>Work email *</label>
<input id="field-email" aria-describedby={error ? "login-error" : undefined} type="email" ... />
{error && <p id="login-error" role="alert" style={errorStyle}>{error}</p>}
```

---

#### A2 · Accessibility — No Skip-to-Main Link
**Slug:** `a11y-skip-to-main` | **File:** `App.tsx:248`

WCAG 2.1 SC 2.4.1 (Bypass Blocks) requires a mechanism to skip repeated navigation. No skip link exists. Keyboard users must tab through all NavBar items on every page.

**Fix:** Add a visually-hidden `<a href="#main-content">Skip to main content</a>` before `<NavBar>`. The `<main>` in `PortalLayout.tsx:77` should receive `id="main-content"`.

---

#### A3 · Accessibility — No ARIA Live Regions on Errors / Loading
**Slug:** `a11y-live-regions` | **Files:** `LoginPage.tsx:194–207`, `App.tsx:199`

Error paragraphs have no `role="alert"` or `aria-live`. The `RequireAuth` loading state is a plain `<div>Loading…</div>` with no `role="status"`. Screen readers do not announce these changes.

**Fix:**
- Add `role="alert"` to the login error `<p>` (auto-assertive).
- Add `role="status" aria-live="polite"` to all loading state containers.

---

#### A4 · Accessibility — Disclosure Buttons Lack `aria-expanded`
**Slug:** `a11y-aria-expanded` | **Files:** `QuizRunner.tsx:226–242`, `LoginPage.tsx:298–317`

`AnsweredAccordion` and the enrollment-code toggle use `<button>` elements that show "▲ collapse" / "▼ expand" text but no `aria-expanded` attribute. WCAG SC 4.1.2 (Name, Role, Value) requires state to be programmatically determinable.

**Fix:** Add `aria-expanded={isOpen}` and `aria-controls="panel-{id}"` to every disclosure button. Give the controlled panel `id="panel-{id}"`.

---

#### A5 · Accessibility — NavBar Landmark Lacks `aria-label`
**Slug:** `a11y-nav-landmark` | **File:** `App.tsx:71`

The `<nav>` has no `aria-label`. If a page has multiple landmark regions (which it does — `PortalBackground` adds decorative DOM and future sidebars may be added), screen reader users cannot distinguish this nav.

**Fix:** Add `aria-label="Main navigation"` to the `<nav>` element.

---

### Tier 2 — High (Design consistency, performance, responsiveness)

#### B1 · Design Consistency — Inline Style Proliferation in LoginPage
**Slug:** `design-inline-style-proliferation` | **File:** `LoginPage.tsx:16–48`

`LoginPage` defines its own `inputStyle`, `labelStyle`, and `btnStyle` JS objects instead of using the global `.form-control`, `.form-group label`, and `.btn.btn-primary` CSS classes already defined in `index.css:242–264` and `index.css:164–173`. This means changes to the global design system do not cascade to the login page.

**Fix:** Replace all inline style objects with global class names. Add `.login-card` to `index.css` for the wrapper.

---

#### B2 · Design Consistency — PortalLayout Color Mismatch
**Slug:** `design-portal-color-mismatch` | **Files:** `PortalLayout.tsx:26–76`, `index.css:34–36`

`PortalLayout.tsx` uses hardcoded `rgba(77, 171, 247, …)` (a light-blue from an earlier palette) for the portal rings and glow, while `index.css` defines the brand palette as indigo-violet (`--primary: #4F46E5`, `--accent: #7C3AED`). This creates a visible hue inconsistency between the background and all foreground UI elements.

**Fix:** Replace `rgba(77, 171, 247, …)` with `rgba(79, 70, 229, …)` (var(--primary) in RGB) or better, use CSS variables directly: `border: 1px solid color-mix(in srgb, var(--primary) 22%, transparent)`.

---

#### B3 · Performance — No Route-Level Code Splitting
**Slug:** `perf-no-code-splitting` | **Files:** `App.tsx:1–21`, `package.json`

All 16 page components are statically imported at the top of `App.tsx`. The Three.js stack (`three@0.168.0`, `@react-three/fiber@8.17.10`, `@react-three/drei@9.122.0`) is estimated to add **~500–700KB gzipped** to the initial bundle. Users on slower connections wait for the entire bundle before seeing anything.

**Fix:** Wrap page imports in `React.lazy()`; add `<Suspense fallback={<Spinner />}>` at the router level. Consider a dynamic `import()` for the `Portal3D` / `SkillCalibration3D` / `SkillRadar3D` components since they are route-specific.

```tsx
// Before
import HomePage from "./pages/HomePage";

// After
const HomePage = React.lazy(() => import("./pages/HomePage"));
```

---

#### B4 · Responsive Design — Fixed-Width Login Panel
**Slug:** `responsive-login-fixed-width` | **File:** `LoginPage.tsx:155–162`

The login card has a hardcoded `width: 380` (pixels in JS style) with no `maxWidth` + fluid fallback. On screens < 400px (common Android viewport) the card clips horizontally. On large screens the fixed width is fine, but the lack of `box-sizing: border-box` + padding protection can cause overflow.

**Fix:** Replace `width: 380` with `width: "min(380px, 100% - 2rem)"` or `maxWidth: "380px", width: "100%"` + add `24px` horizontal padding on the outer container.

---

#### B5 · Responsive Design — No Mobile Navigation
**Slug:** `responsive-navbar-no-mobile-menu` | **File:** `App.tsx:25–38`

The `NavBar` is a horizontal flex row with `height: 52px`. On viewports < 600px, the 7–9 nav links overflow the horizontal space, are clipped or wrap badly, and there is no hamburger menu or collapsible drawer. Deloitte enterprise tools must be usable on tablets and phones.

**Fix:** Add a breakpoint at `max-width: 640px`: hide nav links, show a hamburger `<button aria-label="Open menu" aria-expanded={menuOpen}>`, render a slide-down or overlay drawer holding the same links.

---

### Tier 3 — Medium (Information architecture, interaction polish, i18n)

#### C1 · Information Architecture — No 404 Not Found Page
**Slug:** `ia-no-404-page` | **File:** `App.tsx:392`

The catch-all route is `<Navigate to="/" replace />`. Any mistyped URL silently redirects the user to the home page with no explanation. This is disorienting, especially after sharing a direct link that is slightly malformed.

**Fix:** Create `pages/NotFoundPage.tsx` with a clear message and a "Back to home" link. Wire it as `<Route path="*" element={<NotFoundPage />} />`.

---

#### C2 · Information Architecture — No Breadcrumb Navigation
**Slug:** `ia-no-breadcrumbs` | **Files:** `App.tsx:280–310`

Deep routes (`/practitioners/:id/skills`, `/profile/:profileId/skills`, `/admin/practitioners/:id`) have no breadcrumb trail. Practitioners cannot quickly return to a parent view without using the browser back button.

**Fix:** Create a `<Breadcrumb>` component; render it at the top of `PortalPage`/`PortalLayout`. Drive it from `useMatches()` (React Router v6) with optional `handle.breadcrumb` metadata on each `<Route>`.

---

#### C3 · Interaction Patterns — Hardcoded Error Colors in LoginPage
**Slug:** `interaction-hardcoded-error-colors` | **File:** `LoginPage.tsx:196–200`

The login error state uses `color: "#ef4444"`, `background: "#fef2f2"` — hardcoded hex that does not adapt to dark mode. In dark mode the `#fef2f2` light-pink background is jarring against the dark surface.

**Fix:** Replace with `color: "var(--danger)"` and `background: "color-mix(in srgb, var(--danger) 8%, var(--surface))"` — the same pattern already used correctly in `QuizRunner.tsx:967`.

---

#### C4 · Interaction Patterns — Poor RequireAuth Loading UX
**Slug:** `interaction-requireauth-loading-state` | **File:** `App.tsx:199`

`RequireAuth` shows `<div style={{ padding: "2rem", color: "var(--text-muted)" }}>Loading…</div>` while `/auth/me` is in-flight. This is a visible flash of unstyled text before the page appears. No `role="status"` for screen readers.

**Fix:** Replace with a centered `<span className="spinner" role="status" aria-label="Loading" />` inside a `<div>` with proper `aria-live="polite"` context.

---

#### C5 · i18n Readiness — No Internationalization Infrastructure
**Slug:** `i18n-readiness` | **Files:** All page and component files

All user-visible strings are hardcoded English literals scattered across components (`LoginPage.tsx`, `QuizRunner.tsx`, `App.tsx`, etc.). Deloitte enterprise tools used globally require locale switching. There is no message catalog, no `IntlProvider`, no locale detection.

**Fix (phased approach):**
1. Add `react-intl` (or `i18next`).
2. Create `src/messages/en-US.ts` as the canonical message catalog.
3. Wrap `App` in `<IntlProvider locale="en-US" messages={messages}>`.
4. Replace literal strings with `<FormattedMessage id="..." />` or `intl.formatMessage({id: "..."})`.
5. This is a large surface area — plan as a standalone phase.

---

## Decision Space Summary

### ✅ Already Aligned (Pre-Resolved)

| Slug | Value |
|---|---|
| `css-design-token-system` | CSS custom properties with full light+dark mode |
| `no-browser-storage-policy` | Zero localStorage/sessionStorage |
| `semantic-html-structure` | nav/main/h1-h3/button/form in place |
| `tanstack-query-server-state` | TanStack Query v5 for all server state |
| `loading-error-empty-states` | Spinner, empty-state, error CSS in place |

### ❌ Requires Action (Open Decisions)

| Priority | Slug | Area | Effort |
|---|---|---|---|
| P0 | `a11y-form-label-binding` | Accessibility | S |
| P0 | `a11y-skip-to-main` | Accessibility | XS |
| P0 | `a11y-live-regions` | Accessibility | S |
| P0 | `a11y-aria-expanded` | Accessibility | S |
| P0 | `a11y-nav-landmark` | Accessibility | XS |
| P1 | `design-inline-style-proliferation` | Design Consistency | M |
| P1 | `design-portal-color-mismatch` | Design Consistency | XS |
| P1 | `perf-no-code-splitting` | Performance | M |
| P1 | `responsive-login-fixed-width` | Responsive Design | XS |
| P1 | `responsive-navbar-no-mobile-menu` | Responsive Design | L |
| P2 | `ia-no-404-page` | Information Architecture | S |
| P2 | `ia-no-breadcrumbs` | Information Architecture | M |
| P2 | `interaction-hardcoded-error-colors` | Interaction Patterns | XS |
| P2 | `interaction-requireauth-loading-state` | Interaction Patterns | XS |
| P3 | `i18n-readiness` | Component System | XL |

---

## Constraint Gate Results

| Constraint | Status | Detail |
|---|---|---|
| No browser storage | ✅ PASS | Zero localStorage/sessionStorage confirmed |
| WCAG 2.1 AA | ❌ FAIL | 5 violations (A1–A5 above) |
| Mobile responsive | ❌ FAIL | Fixed login width, no mobile nav |
| Design token consistency | ⚠️ PARTIAL | CSS vars in place; PortalLayout and LoginPage bypass them |
| Performance budget | ❌ FAIL | No code splitting; Three.js bundle unoptimized |
| Error state UX | ⚠️ PARTIAL | Errors exist but lack ARIA; LoginPage uses hardcoded colors |

---

## Recommended Phasing

**Phase A — Accessibility Sprint** (P0, 1–2 days)
Fix A1–A5 in LoginPage, App.tsx, QuizRunner, PortalLayout. These are low-effort changes that unlock WCAG compliance and unblock any formal accessibility audit.

**Phase B — Design Consistency & Performance** (P1, 2–3 days)
- Migrate LoginPage to global CSS classes (B1)
- Fix PortalLayout colors (B2)
- Add React.lazy + Suspense for all 16 page routes (B3)
- Fix login card responsive width (B4)
- Add hamburger mobile nav (B5)

**Phase C — IA & Interaction Polish** (P2, 1–2 days)
- 404 page (C1)
- Breadcrumb component (C2)
- Fix error colors and loading states (C3, C4)

**Phase D — i18n** (P3, dedicated sprint)
- Message catalog extraction + IntlProvider wiring (C5)

---

## Solution Overview

The Mastery Pulse frontend has a **well-designed foundation** but needs targeted hardening across accessibility, responsive design, and performance to meet Deloitte enterprise standards. All proposed fixes are contained within the existing React/TypeScript/Vite stack — no framework changes are needed. The largest single effort is mobile navigation (B5) and i18n (Phase D).

Key architectural decisions to preserve (all correct):
- **TanStack Query** for server state — do not add useState for server data
- **HttpOnly cookie + no browser storage** — do not cache session data client-side
- **CSS custom properties** design token system — extend it, do not bypass it
- **TypeScript strict mode** — maintain type safety in all new components
