# Design System
## AI Customer Support Agent

**Version:** 1.0
**Last updated:** July 27, 2026

Theme: Light + Dark (toggle) · Mood: Warm/Friendly · Typography: Classic/Neutral

---

## 1. Color Palette

### 1.1 Brand & Accent Colors

| Token | Hex | Usage |
|---|---|---|
| `--color-primary` | `#E8722C` | Primary buttons, links, active states |
| `--color-primary-hover` | `#D4611F` | Hover state for primary elements |
| `--color-primary-light` | `#FBD9BD` | Subtle backgrounds, badges, highlights |
| `--color-accent` | `#F2A65A` | Secondary accents, icons, highlights |
| `--color-accent-soft` | `#FFF1E0` | Soft background tint (cards, chat bubbles) |

### 1.2 Light Mode

| Token | Hex | Usage |
|---|---|---|
| `--bg-base` | `#FDFBF8` | Page background |
| `--bg-surface` | `#FFFFFF` | Cards, chat window, panels |
| `--bg-muted` | `#F5EFE8` | Muted sections, input backgrounds |
| `--text-primary` | `#2B2116` | Main body text |
| `--text-secondary` | `#6B5D4F` | Secondary/help text |
| `--border` | `#E8DFD3` | Dividers, card borders |
| `--success` | `#3FA65D` | Resolved tickets, success states |
| `--warning` | `#E0A62A` | Pending/attention states |
| `--danger` | `#D64545` | Errors, urgent priority |

### 1.3 Dark Mode

| Token | Hex | Usage |
|---|---|---|
| `--bg-base` | `#1C1712` | Page background |
| `--bg-surface` | `#2A2219` | Cards, chat window, panels |
| `--bg-muted` | `#332A1F` | Muted sections, input backgrounds |
| `--text-primary` | `#F5EFE8` | Main body text |
| `--text-secondary` | `#C4B7A6` | Secondary/help text |
| `--border` | `#453A2C` | Dividers, card borders |
| `--success` | `#5FC97D` | Resolved tickets, success states |
| `--warning` | `#F0BE55` | Pending/attention states |
| `--danger` | `#E86A6A` | Errors, urgent priority |

Primary/accent colors stay the same across both modes; only backgrounds, text, and borders shift.

### 1.4 Semantic Usage

| Element | Color |
|---|---|
| Customer message bubble | `--color-accent-soft` background, `--text-primary` text |
| Agent (AI) message bubble | `--bg-surface` background, `--text-primary` text, `--border` outline |
| Ticket status: open | `--warning` |
| Ticket status: resolved | `--success` |
| Ticket status: urgent priority | `--danger` |
| Escalation banner | `--color-primary` background, white text |
| Links / interactive text | `--color-primary` |

---

## 2. Typography

### 2.1 Font Family

- **Primary font:** Roboto
- **Fallback stack:** `"Roboto", "Helvetica Neue", Helvetica, Arial, sans-serif`

```css
--font-family-base: "Roboto", "Helvetica Neue", Helvetica, Arial, sans-serif;
```

Load via Google Fonts or self-hosted:
```html
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;600;700&display=swap" rel="stylesheet">
```

### 2.2 Type Scale

| Token | Size | Weight | Usage |
|---|---|---|---|
| `--text-xs` | 12px | 400 | Timestamps, captions |
| `--text-sm` | 14px | 400 | Secondary text, labels |
| `--text-base` | 16px | 400 | Body text, chat messages |
| `--text-lg` | 18px | 500 | Section headers (small) |
| `--text-xl` | 22px | 600 | Page headers |
| `--text-2xl` | 28px | 700 | Dashboard titles |

### 2.3 Line Height & Spacing

- Body text: `line-height: 1.5`
- Headings: `line-height: 1.25`
- Paragraph spacing: `margin-bottom: 0.75rem`

---

## 3. Theme Tokens (CSS Variables)

```css
:root {
  /* Brand */
  --color-primary: #E8722C;
  --color-primary-hover: #D4611F;
  --color-primary-light: #FBD9BD;
  --color-accent: #F2A65A;
  --color-accent-soft: #FFF1E0;

  /* Light mode (default) */
  --bg-base: #FDFBF8;
  --bg-surface: #FFFFFF;
  --bg-muted: #F5EFE8;
  --text-primary: #2B2116;
  --text-secondary: #6B5D4F;
  --border: #E8DFD3;
  --success: #3FA65D;
  --warning: #E0A62A;
  --danger: #D64545;

  /* Typography */
  --font-family-base: "Roboto", "Helvetica Neue", Helvetica, Arial, sans-serif;
  --text-xs: 12px;
  --text-sm: 14px;
  --text-base: 16px;
  --text-lg: 18px;
  --text-xl: 22px;
  --text-2xl: 28px;
}

[data-theme="dark"] {
  --bg-base: #1C1712;
  --bg-surface: #2A2219;
  --bg-muted: #332A1F;
  --text-primary: #F5EFE8;
  --text-secondary: #C4B7A6;
  --border: #453A2C;
  --success: #5FC97D;
  --warning: #F0BE55;
  --danger: #E86A6A;
}
```

For Tailwind, map these tokens into `tailwind.config.ts` under `theme.extend.colors` so components use `bg-surface`, `text-primary`, etc. instead of raw hex values.

---

## 4. Component Style Notes

- **Border radius:** `8px` for buttons/inputs, `12px` for cards and chat bubbles. Keep it consistent, warm/friendly favors slightly rounded over sharp corners.
- **Shadows:** soft, low-opacity shadows only (`0 2px 8px rgba(0,0,0,0.06)` in light mode, slightly stronger in dark mode). Avoid harsh drop shadows.
- **Buttons:** primary uses `--color-primary` fill with white text; secondary uses `--bg-muted` fill with `--text-primary` text and a `--border` outline.
- **Chat widget:** rounded bubbles, generous padding (`12px 16px`), clear visual distinction between customer and agent messages (see 1.4 Semantic Usage).
- **Dark mode toggle:** persist user preference (e.g. in a cookie or local component state — no `localStorage` inside any AI-generated artifact previews, but fine in the real Next.js app).

---

### Related documents
- PRD: `ai-support-agent-prd.md`
- TRD: `ai-support-agent-trd.md`
- Architecture: `architecture.md`
- Rules: `rules.md`
- Phases: `phases.md`
