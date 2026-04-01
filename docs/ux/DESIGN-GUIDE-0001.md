# Design Guide: Minimalist GameCube Aesthetic

**Version**: 1.0
**Status**: Approved
**Applies to**: ResumeTailor V1 UI

This guide translates the iconic industrial design of the Nintendo GameCube into a modern,
minimalist web interface for ResumeTailor.

If this design guide conflicts with [UX-0001.md](UX-0001.md) on user-facing behavior, the UX spec wins.

---

## 1. Color Palette

The GameCube era was defined by bold, saturated colors paired with neutral tech-greys.

| Token | Name | Hex | Usage |
|-------|------|-----|-------|
| `--color-primary` | Indigo | `#6A5ACD` | Primary brand elements, headers, active states |
| `--color-primary-dark` | Deep Indigo | `#4B0082` | Hover and pressed states on primary elements |
| `--color-accent` | Spice Orange | `#FF8C00` | CTA buttons, highlights, interactive affordances |
| `--color-surface` | Platinum Grey | `#E5E4E2` | Card backgrounds, secondary containers |
| `--color-surface-alt` | Light Platinum | `#D3D3D3` | Subtle dividers, disabled surface backgrounds |
| `--color-text` | Jet Black | `#1A1A1A` | Body text, high-contrast readability, deep soft shadows |
| `--color-error` | Power LED Red | `#FF0000` | Error states, "on" indicator accents only -- use sparingly |

---

## 2. Typography

Fonts that feel tech-forward but friendly, echoing the early 2000s digital aesthetic.

### Headings

- **Preferred**: Orbitron, Michroma, or Roboto Mono
- **Style**: Wide, geometric sans-serifs
- **Usage**: Section headers, card titles, modal headings

### Body

- **Preferred**: Inter or Open Sans
- **Style**: Highly legible sans-serif with generous tracking (`letter-spacing: 0.01em`)
- **Usage**: Paragraphs, labels, input hints, button text

### Display

- **Style**: Squarish, blocky fonts for large hero or section headers
- **Purpose**: Mimics the console's rectangular silhouette
- **Usage**: Hero copy, primary panel title, empty state messaging

---

## 3. UI Elements and Shapes

The GameCube's physical form is the blueprint.

### The Handle Motif

- Incorporate rounded rectangular shapes with cutout or handle-like negative space in
  headers and sidebars
- Example: sidebar nav with a visible "grip" cutout on the right edge

### Circular Vents

- Use subtle circular dot patterns (`radial-gradient` or SVG dot grid) in section backgrounds
  to reference the console's cooling vents
- Opacity: 8-12% so the texture is felt, not seen

### Beveled Edges

- `border-radius`: 12px for inputs and cards; 16px-24px for primary panels and modals
- Pair with a subtle inner shadow to create a tactile, plastic feel:

```css
box-shadow: inset 0 1px 2px rgba(255, 255, 255, 0.6),
            0 4px 16px rgba(26, 26, 26, 0.15);
```

### Glossy Surfaces

- High-shine gradients on primary buttons and the active disc lid metaphor:

```css
background: linear-gradient(
  135deg,
  #7B6FD8 0%,
  #6A5ACD 45%,
  #5849B8 100%
);
```

---

## 4. Interaction Design

### Tactile Feedback

Buttons must have a clear press animation mimicking the satisfying click of the GameCube
shoulder buttons.

```css
button:active {
  transform: translateY(2px) scale(0.98);
  box-shadow: 0 1px 4px rgba(26, 26, 26, 0.2);
  transition: transform 80ms ease, box-shadow 80ms ease;
}
```

### Loading States

Two approved loading patterns:

1. **Spinning Disc**: Animated circular element that rotates at a constant 1.5 RPM to
   reference the top-loading disc lid
2. **Pulsating Power LED**: A small `#FF0000` dot that fades in and out with a 2 second
   period -- used for background task indicators

### Layout

- Grid-based layout centered around a main "core" content area
- Primary content column: `max-width: 960px`, centered
- Two-column review layout (source | edited): `1fr 1fr` with a 24px gap
- All panels feel solid and balanced; avoid asymmetric chrome

---

## 5. Iconography

### Shape Container Rule

All icons must be contained within a circle or a square with `border-radius: 8px`.
No bare/uncontained icons in primary UI surfaces.

### Two-Tone Color Rule

- **Fill**: Indigo (`#6A5ACD`)
- **Accent stroke or highlight**: Spice Orange (`#FF8C00`)
- This keeps all icons consistent with the brand and instantly recognisable

### Icon Size Scale

| Context | Size |
|---------|------|
| Inline / body text | 16px |
| Button prefix | 20px |
| Card header | 24px |
| Empty state / hero | 48px |

---

## 6. Design Tokens (CSS Custom Properties)

Consume these tokens in all stylesheets and inline styles. Do not hardcode hex values in
component files.

```css
:root {
  /* Colors */
  --color-primary:      #6A5ACD;
  --color-primary-dark: #4B0082;
  --color-accent:       #FF8C00;
  --color-surface:      #E5E4E2;
  --color-surface-alt:  #D3D3D3;
  --color-text:         #1A1A1A;
  --color-error:        #FF0000;

  /* Typography */
  --font-heading: 'Orbitron', 'Michroma', monospace;
  --font-body:    'Inter', 'Open Sans', sans-serif;

  /* Shape */
  --radius-sm:  12px;
  --radius-md:  16px;
  --radius-lg:  24px;

  /* Spacing scale (4px base) */
  --space-1:  4px;
  --space-2:  8px;
  --space-3:  12px;
  --space-4:  16px;
  --space-6:  24px;
  --space-8:  32px;
  --space-12: 48px;

  /* Shadows */
  --shadow-card:   0 4px 16px rgba(26, 26, 26, 0.15);
  --shadow-inset:  inset 0 1px 2px rgba(255, 255, 255, 0.6);
  --shadow-button: 0 2px 8px rgba(106, 90, 205, 0.4);
}
```

---

## 7. Anti-Patterns

The following MUST NOT appear in ResumeTailor UI components:

- Flat, all-white backgrounds with no surface depth -- always use `--color-surface` or a
  gradient
- Non-geometric, organic icon shapes (no blobs or freeform curves)
- More than two accent colors visible in a single view (Indigo + Orange only)
- `border-radius` smaller than 8px on any interactive element
- Hardcoded color hex values outside of this token set
- `#FF0000` Power LED Red used for anything other than errors or status indicators
