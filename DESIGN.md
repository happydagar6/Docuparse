# Litwise — Design System & UI Specifications (DESIGN.md)

---

## 1. Design Philosophy & Aesthetic Vision

Litwise follows an **academic, high-density, yet distraction-free aesthetic** tailored for deep reading, analytical thinking, and research synthesis. 

### Key Principles:
* **Clarity Over Clutter**: Generous whitespace, clean typography, and zero flashy gimmicks that distract from complex academic content.
* **Perceptual Uniformity**: Built entirely on modern **OKLCH color space**, ensuring consistent contrast ratios across both pristine light mode and high-contrast dark mode.
* **Citation-First Affordances**: Citations are not plain text footnotes; they are interactive, badge-styled pills (`[Page 4]`) that link directly to the synchronized PDF viewport.
* **Responsive Split-Pane**: A balanced two-column layout allowing researchers to read the original source PDF while interacting with the AI assistant, taking notes, or generating study plans.

---

## 2. Color Palette & Design Tokens

Litwise utilizes Tailwind CSS v4 inline themes defined in [`src/app/globals.css`](file:///c:/Users/harsh/OneDrive/Desktop/Litwise%20Project/litwise-frontend/src/app/globals.css).

### 2.1 Core Palette Tokens (OKLCH)

| Token Name | Light Mode (OKLCH) | Dark Mode (OKLCH) | Usage |
| :--- | :--- | :--- | :--- |
| **`--background`** | `oklch(1 0 0)` (Pure White) | `oklch(0.145 0 0)` (Deep Charcoal) | Canvas background |
| **`--foreground`** | `oklch(0.145 0 0)` (Near Black) | `oklch(0.985 0 0)` (Clean White) | Primary text content |
| **`--card`** | `oklch(1 0 0)` | `oklch(0.205 0 0)` | Card containers & sidebars |
| **`--card-foreground`**| `oklch(0.145 0 0)` | `oklch(0.985 0 0)` | Card text |
| **`--primary`** | `oklch(0.205 0 0)` (Graphite) | `oklch(0.922 0 0)` (Crisp White) | Primary CTA buttons & active states |
| **`--primary-foreground`**| `oklch(0.985 0 0)` | `oklch(0.205 0 0)` | Text inside primary buttons |
| **`--secondary`** | `oklch(0.97 0 0)` (Soft Gray) | `oklch(0.269 0 0)` (Muted Slate) | Secondary actions, badges |
| **`--muted`** | `oklch(0.97 0 0)` | `oklch(0.269 0 0)` | Subdued backgrounds |
| **`--muted-foreground`** | `oklch(0.556 0 0)` | `oklch(0.708 0 0)` | Captions, dates, metadata |
| **`--accent`** | `oklch(0.97 0 0)` | `oklch(0.269 0 0)` | Hover highlights, active tab pills |
| **`--destructive`** | `oklch(0.577 0.245 27.325)` | `oklch(0.704 0.191 22.216)` | Errors, delete actions, warnings |
| **`--border`** | `oklch(0.922 0 0)` | `oklch(1 0 0 / 10%)` | Subtle separation lines |
| **`--ring`** | `oklch(0.708 0 0)` | `oklch(0.556 0 0)` | Accessibility focus rings |

### 2.2 Data Visualization & Chart Scale
* **`--chart-1`**: `oklch(0.646 0.222 41.116)` (Warm Amber / Orange)
* **`--chart-2`**: `oklch(0.6 0.118 184.704)` (Cyan / Aqua)
* **`--chart-3`**: `oklch(0.398 0.07 227.392)` (Deep Ocean Blue)
* **`--chart-4`**: `oklch(0.828 0.189 84.429)` (Chartreuse Yellow)
* **`--chart-5`**: `oklch(0.769 0.188 70.08)` (Coral Red)

### 2.3 Sidebar Tokens
* Dedicated sidebar background, text, accent, and border variables (`--sidebar`, `--sidebar-foreground`, `--sidebar-accent`, `--sidebar-border`) to visually separate document navigation from the workspace.

---

## 3. Typography & Hierarchy

Litwise pairs modern sans-serif typefaces for readability with monospace fonts for math, citations, and code snippets.

### 3.1 Font Families
* **Primary Sans (`--font-sans`)**: `Geist Sans` (`var(--font-geist-sans)`), with system fallbacks (`-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, `Inter`, `sans-serif`).
* **Code & Monospace (`--font-mono`)**: `Geist Mono` (`var(--font-geist-mono)`), with fallbacks (`JetBrains Mono`, `Consolas`, `monospace`).

### 3.2 Type Hierarchy

| Level | Size / Weight | Line Height | Usage |
| :--- | :--- | :--- | :--- |
| **Display Title (H1)** | `2.25rem (36px)` / `700 (Bold)` | `1.2` | Workspace title, paper title |
| **Section Header (H2)** | `1.5rem (24px)` / `600 (Semibold)` | `1.3` | Module headings (Quiz, Study Plan) |
| **Subheader (H3)** | `1.125rem (18px)` / `600 (Semibold)` | `1.4` | Chat section labels, modal titles |
| **Body (Default)** | `0.875rem (14px)` / `400 (Regular)` | `1.6` | Chat message text, document notes |
| **Body Large** | `1.0rem (16px)` / `400 (Regular)` | `1.5` | Executive summaries, quiz questions |
| **Caption / Metadata** | `0.75rem (12px)` / `500 (Medium)` | `1.4` | Timestamps, page numbers, tags |
| **Citation Badge** | `0.75rem (12px)` / `600 (Semibold)` | `1.0` | `[Page X]` clickable pill badges |

---

## 4. Spacing, Elevation & Layout Grid

### 4.1 Border Radii
* **Base Radius (`--radius`)**: `0.625rem` (10px)
* **Small (`--radius-sm`)**: `calc(var(--radius) - 4px)` = `6px` (tags, buttons)
* **Medium (`--radius-md`)**: `calc(var(--radius) - 2px)` = `8px` (inputs, cards)
* **Large (`--radius-lg`)**: `var(--radius)` = `10px` (modal dialogues, dialogs)
* **Extra Large (`--radius-xl`)**: `calc(var(--radius) + 4px)` = `14px` (outer workspace containers)

### 4.2 Workspace Layout (The Split-Screen Paradigm)

```
+-------------------------------------------------------------------------+
| Top Navigation Bar (Logo, Active Paper Title, Upload, Theme Switcher)   |
+------------------------------------+------------------------------------+
| LEFT PANE: PDF Viewer (50%)        | RIGHT PANE: Research Studio (50%)  |
|                                    | Tabs: [Chat] [Study] [Quiz] [Notes]|
| - Zoom Controls (+ / - / Fit)      |                                    |
| - Thumbnail Drawer / Page Jumper   | - Real-time SSE Streaming Chat     |
| - High-Fidelity Canvas (React-PDF) | - Interactive Citation Badges      |
| - Text Selection & Highlight Layer | - TipTap Collaborative Note Editor |
|                                    | - Adaptive Quiz Cards & Feedback   |
|                                    |                                    |
+------------------------------------+------------------------------------+
```

---

## 5. Key Interactive Components

### 5.1 Chat Bubble & Streaming Cursor
* **User Messages**: Right-aligned, subtle muted background (`bg-muted/70`), crisp border.
* **Assistant Messages**: Left-aligned, transparent card background, markdown rendered with syntax-highlighted code blocks and LaTeX math via `recharts` / `react-markdown`.
* **Streaming Indicator**: A pulsing cursor block (`animate-pulse`) while tokens are arriving via SSE.

### 5.2 Citation Badges (`[Page X]`)
* Styled as inline badges with `bg-secondary hover:bg-primary hover:text-primary-foreground transition-colors cursor-pointer`.
* Clicking a badge dispatches a custom event to the synchronized PDF viewport on the left, automatically scrolling to the target page and highlighting the source sentence.

### 5.3 TipTap Research Editor
* Floating bubble menu for bold, italic, headings, equations, and literature citations.
* Tables extension with customizable borders and row headers.
