# Style Guide Reference

The Power BI Creator Skill uses a JSON-based style guide to enforce consistent report styling. This document describes every field, how data colors work, how category detection operates, and the layout rules the engine enforces.

## File Format

A style guide is a JSON object with the following top-level sections:

```json
{
  "dataColors": [...],
  "backgrounds": {...},
  "categoryColors": {...},
  "layoutRules": {...},
  "typography": {...},
  "colors": {...},
  "pageStructure": {...},
  "visualTypeRules": {...},
  "rules": {...}
}
```

All sections are optional — the engine applies only the sections present.

---

## `dataColors`

An ordered array of hex color strings that define the report's primary palette.

```json
"dataColors": [
  "#E8734A",
  "#D4A27F",
  "#C9CBA3",
  "#7A9E7E",
  "#3C6E71",
  "#284B63",
  "#1A1A2E",
  "#F2E8CF",
  "#BC6C25",
  "#606C38"
]
```

### How data colors work

1. When a style guide with `dataColors` is applied, the engine **injects a Power BI custom theme** into the report's `StaticResources/RegisteredResources/` folder.
2. The custom theme sets the `dataColors` array in the theme JSON, which Power BI uses as the default palette for all chart series.
3. Charts with **category or series fields** automatically pick up colors from this palette in order.
4. **Single-series charts** (e.g., a KPI card) can be individually colored via `objects.dataPoint` with a direct fill color instead of relying on the theme.

### Theme injection details

The injected theme file has this structure:

```json
{
  "name": "CustomStyleGuideTheme",
  "dataColors": ["#E8734A", "#D4A27F", ...],
  "background": "#FFFFFF",
  "foreground": "#1A1A2E",
  "tableAccent": "#E8734A"
}
```

It is registered in the report definition under:
- `themeCollection` with `type: "RegisteredResources"`
- `resourcePackages` with `type: "CustomTheme"`

---

## `backgrounds`

Controls page and visual background fills.

```json
"backgrounds": {
  "page": {
    "color": "#FFFFFF",
    "transparency": 0
  },
  "visual": {
    "color": "#FFFFFF",
    "transparency": 100
  }
}
```

| Field | Type | Description |
|---|---|---|
| `page.color` | hex string | Page background fill color |
| `page.transparency` | integer (0–100) | 0 = fully opaque, 100 = fully transparent |
| `visual.color` | hex string | Default visual container background |
| `visual.transparency` | integer (0–100) | Visual background transparency |

---

## `categoryColors`

A mapping from **dimension values** to specific colors. Used for deterministic coloring of known categories (e.g., status fields, regions).

```json
"categoryColors": {
  "Active": "#7A9E7E",
  "Inactive": "#BC6C25",
  "Pending": "#D4A27F",
  "Completed": "#3C6E71",
  "Cancelled": "#E8734A"
}
```

### How category detection works

1. When the style engine encounters a visual with a **category axis** or **legend field**, it inspects the field's known values.
2. If any value matches a key in `categoryColors`, the engine applies the corresponding color via `objects.dataPoint` conditions.
3. Matching is **case-insensitive** — `"active"`, `"Active"`, and `"ACTIVE"` all match.
4. Values not found in the map fall back to the `dataColors` palette in order.
5. Category colors take precedence over theme data colors for matched values.

---

## `layoutRules`

Defines spacing and positioning constraints that the validation engine enforces.

```json
"layoutRules": {
  "gap": 20,
  "margin": 20,
  "preventOverlaps": true
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `gap` | integer (px) | 20 | Minimum space between adjacent visuals, both horizontal and vertical |
| `margin` | integer (px) | 20 | Minimum space between any visual edge and the page boundary |
| `preventOverlaps` | boolean | `true` | When `true`, the validation engine blocks any write that would create overlapping visuals |

### Layout enforcement

- The engine checks **every visual pair** on a page for overlap after any add/move/resize operation.
- If `preventOverlaps` is `true` and an overlap is detected, the operation is **rejected** with an error listing the conflicting visuals.
- Gap enforcement is advisory during `dry_run` and strict during actual writes.
- The `rearrange_page_visuals` tool can automatically fix spacing issues by redistributing visuals within the page bounds.

---

## `typography`

Controls global and per-element font styling across the report.

```json
"typography": {
  "fontFamily": "Segoe UI",
  "elements": {
    "pageTitle": { "size": 24, "weight": "bold", "color": "#1A1A2E" },
    "subtitle": { "size": 14, "weight": "normal", "color": "#606C38" },
    "visualTitle": { "size": 12, "weight": "semibold" },
    "filterBarTitle": { "size": 11, "weight": "bold" },
    "axisLabels": { "size": 10, "weight": "normal" },
    "filterValues": { "size": 10, "weight": "normal" },
    "tableHeaders": { "size": 11, "weight": "bold", "color": "#284B63" },
    "tableTotals": { "size": 11, "weight": "bold" },
    "kpiValues": { "size": 28, "weight": "bold", "color": "#E8734A" }
  }
}
```

| Field | Type | Description |
|---|---|---|
| `fontFamily` | string \| null | Global font family override applied to every text element in the report. When `null`, Power BI's default font is used. |
| `elements` | object \| null | Per-element font specs. Each key maps to an object with `size` (integer, pt), `weight` (`"normal"`, `"semibold"`, `"bold"`), and optional `color` (hex string). |

### Supported element keys

| Key | Applies to |
|---|---|
| `pageTitle` | Page title text boxes |
| `subtitle` | Subtitle text boxes |
| `visualTitle` | Visual header titles |
| `filterBarTitle` | Filter pane section headers |
| `axisLabels` | Chart axis tick labels |
| `filterValues` | Filter pane value labels |
| `tableHeaders` | Table and matrix column headers |
| `tableTotals` | Table and matrix total rows |
| `kpiValues` | KPI card primary value text |

---

## `colors`

Unified color management via the `StyleGuideColors` schema. Centralises all color definitions in one place.

```json
"colors": {
  "reportPalette": {
    "primary": [
      { "name": "Brand Orange", "hex": "#E8734A", "token": "brand-primary", "usage": "Accent, CTA" }
    ],
    "secondary": [
      { "name": "Forest", "hex": "#3C6E71", "usage": "Supporting charts" }
    ],
    "tertiary": [
      { "name": "Sand", "hex": "#F2E8CF" }
    ]
  },
  "visualPalette": ["#E8734A", "#3C6E71", "#284B63", "#7A9E7E", "#D4A27F"],
  "sentiment": {
    "positive": "#7A9E7E",
    "negative": "#E8734A",
    "neutral": "#C9CBA3"
  },
  "divergent": {
    "max": "#3C6E71",
    "middle": "#F2E8CF",
    "min": "#E8734A"
  },
  "themeAdvanced": {
    "firstLevel": "#E8734A",
    "secondLevel": "#D4A27F",
    "thirdLevel": "#C9CBA3",
    "fourthLevel": "#7A9E7E",
    "background": "#FFFFFF",
    "secondaryBackground": "#F2E8CF"
  },
  "categoryColors": {
    "Active": "#7A9E7E",
    "Inactive": "#BC6C25"
  }
}
```

| Field | Type | Description |
|---|---|---|
| `reportPalette` | object | Tiered report UI colors with `primary`, `secondary`, and `tertiary` arrays. Each entry has `name` (string), `hex` (string), and optional `token` (string) and `usage` (string). |
| `visualPalette` | array of hex strings | Ordered data colors for chart series. When present, replaces `theme.dataColors` in the injected theme. |
| `sentiment` | object | Indicator colors with `positive`, `negative`, and `neutral` hex values. Used by KPI cards, conditional formatting, and trend indicators. |
| `divergent` | object | Gradient endpoints with `max`, `middle`, and `min` hex values. Used for divergent analysis gradients such as heat maps. |
| `themeAdvanced` | object | Power BI theme advanced elements: `firstLevel`, `secondLevel`, `thirdLevel`, `fourthLevel`, `background`, `secondaryBackground`. Maps directly to the PBI theme JSON advanced color slots. |
| `categoryColors` | object | Dimension-value → color map. Promoted from the top-level `categoryColors` section; when specified here, takes precedence over the top-level key. |

---

## `pageStructure`

Defines a zone-based page layout that divides each page into header, body, footer, and filter panel regions.

```json
"pageStructure": {
  "canvas": { "width": 1280, "height": 720 },
  "header": {
    "height": 80,
    "backgroundColor": "#1A1A2E",
    "elements": {
      "logo": { "url": "https://example.com/logo.png", "width": 120, "height": 40, "x": 20, "y": 20, "name": "CompanyLogo" }
    }
  },
  "footer": {
    "height": 40,
    "backgroundColor": "#F2E8CF",
    "elements": {
      "disclaimer": { "width": 400, "height": 20, "x": 440, "y": 10 }
    },
    "navigationItems": ["Overview", "Detail", "Appendix"]
  },
  "filterPanel": {
    "side": "left",
    "width": 200,
    "topPadding": 10,
    "backgroundColor": "#FFFFFF"
  },
  "body": {
    "leftMargin": 20,
    "rightMargin": 20,
    "topMargin": 10,
    "bottomMargin": 10,
    "innerPadding": 16,
    "interVisualGap": 12
  }
}
```

| Field | Type | Description |
|---|---|---|
| `canvas` | object | Page dimensions: `width` and `height` in pixels. Default `1280×720`. |
| `header` | object | Top zone: `height` (px), optional `backgroundColor` (hex), optional `elements` map of `ImagePlacement` objects. |
| `footer` | object | Bottom zone: `height` (px), optional `backgroundColor`, optional `elements`, optional `navigationItems` (array of page display names for navigation buttons). |
| `filterPanel` | object | Side filter zone: `side` (`"left"` or `"right"`), `width` (px), `topPadding` (px), optional `backgroundColor`. |
| `body` | object | Content zone: `leftMargin`, `rightMargin`, `topMargin`, `bottomMargin` (px), `innerPadding` (px between body edge and visuals), `interVisualGap` (px between visuals). |

### `ImagePlacement`

| Field | Type | Description |
|---|---|---|
| `url` | string \| null | Image URL. When provided, the engine injects an image visual. |
| `width` | integer | Width in pixels |
| `height` | integer | Height in pixels |
| `x` | integer | Horizontal offset within the zone |
| `y` | integer | Vertical offset within the zone |
| `name` | string \| null | Optional visual name for identification |

---

## `visualTypeRules`

Deep per-visual-type formatting rules. Each key is a Power BI visual type name (e.g., `tableEx`, `pivotTable`, `barChart`, `lineChart`).

```json
"visualTypeRules": {
  "tableEx": {
    "header": { "bgColor": "#284B63", "fontSize": 11, "fontWeight": "bold", "fontColor": "#FFFFFF" },
    "values": { "bgColor": ["#FFFFFF", "#F2E8CF"], "fontSize": 10, "fontWeight": "normal", "fontColor": "#1A1A2E" },
    "total": { "bgColor": "#C9CBA3", "fontSize": 11, "fontWeight": "bold", "fontColor": "#1A1A2E" }
  },
  "barChart": {
    "xAxis": { "fontSize": 10, "fontColor": "#606C38" },
    "yAxis": { "fontSize": 10, "fontColor": "#606C38" },
    "legend": { "fontSize": 9, "fontColor": "#1A1A2E", "position": "top" },
    "labels": { "fontSize": 9, "fontColor": "#1A1A2E" },
    "variants": {
      "compact": { "xAxis": { "fontSize": 8 }, "yAxis": { "fontSize": 8 }, "labels": { "fontSize": 8 } }
    },
    "defaultVariant": "compact"
  }
}
```

### Structure

| Field | Type | Description |
|---|---|---|
| `header` | `VisualElementStyle` | Table/matrix column header styling |
| `values` | `VisualElementStyle` | Table/matrix data row styling |
| `total` | `VisualElementStyle` | Table/matrix total row styling |
| `xAxis` | `VisualElementStyle` | Chart X-axis styling |
| `yAxis` | `VisualElementStyle` | Chart Y-axis styling |
| `legend` | `VisualElementStyle` | Chart legend styling |
| `labels` | `VisualElementStyle` | Chart data label styling |
| `variants` | object | Named alternative style sets. Each key maps to a partial `VisualTypeRules` override. |
| `defaultVariant` | string | Name of the variant to apply by default when no variant is explicitly selected. |

### `VisualElementStyle`

| Field | Type | Description |
|---|---|---|
| `bgColor` | string \| array | Background color. A single hex string for solid fill, or an array of hex strings for alternating row colors (tables only). |
| `fontSize` | integer | Font size in points |
| `fontWeight` | string | `"normal"`, `"semibold"`, or `"bold"` |
| `fontColor` | string | Hex color for text |
| `position` | string | Placement hint (e.g., `"top"`, `"bottom"`, `"right"` for legends) |

---

## Extended `layoutRules`

In addition to the base fields (`gap`, `margin`, `preventOverlaps`), the layout section supports:

| Field | Type | Default | Description |
|---|---|---|---|
| `dimensionSnap` | integer \| null | `null` | When set, all visual dimensions (x, y, width, height) are snapped to the nearest multiple of this value. Common values are `4` or `8` for pixel-grid alignment. |

```json
"layoutRules": {
  "gap": 20,
  "margin": 20,
  "preventOverlaps": true,
  "dimensionSnap": 8
}
```

---

## Extended `rules`

Validation rules that the `validate_style_compliance` tool checks before publishing.

| Field | Type | Default | Description |
|---|---|---|---|
| `titlePattern` | string \| null | `null` | A regex pattern that every visual title must match. For example, `"^[A-Z]"` enforces titles starting with an uppercase letter. |
| `approvedFonts` | array of strings \| null | `null` | When set, only these font family names are allowed. Any visual using a font not in the list is flagged as non-compliant. |

```json
"rules": {
  "titlePattern": "^[A-Z][A-Za-z0-9 ]+$",
  "approvedFonts": ["Segoe UI", "DIN", "Arial"]
}
```

---

## New Tools

### `apply_page_structure`

Applies the zone-based layout defined in the `pageStructure` section to a report page. The tool:

1. Sets the page canvas size from `canvas.width` and `canvas.height`.
2. Creates or repositions header, footer, and filter panel background visuals.
3. Injects image visuals for any `elements` entries that have a `url`.
4. Calculates the available body region and adjusts visual positions to respect zone boundaries.
5. Generates navigation buttons from `footer.navigationItems` if specified.

### `validate_style_compliance`

Performs a full pre-publish validation checklist against the active style guide. Checks include:

- **Font compliance** — all fonts match `rules.approvedFonts` (if set).
- **Title pattern** — all visual titles match `rules.titlePattern` (if set).
- **Color compliance** — all colors used in visuals exist in `dataColors`, `colors.visualPalette`, or `colors.categoryColors`.
- **Layout compliance** — spacing, margins, overlaps, and `dimensionSnap` alignment.
- **Zone compliance** — visuals stay within their assigned `pageStructure` zones.
- **Typography compliance** — element font sizes and weights match `typography.elements` specs.

Returns a structured report listing each violation with the affected visual, rule, and suggested fix.

---

## Complete Example

```json
{
  "dataColors": [
    "#E8734A",
    "#D4A27F",
    "#C9CBA3",
    "#7A9E7E",
    "#3C6E71",
    "#284B63",
    "#1A1A2E",
    "#F2E8CF",
    "#BC6C25",
    "#606C38"
  ],
  "backgrounds": {
    "page": {
      "color": "#FFFFFF",
      "transparency": 0
    },
    "visual": {
      "color": "#FFFFFF",
      "transparency": 100
    }
  },
  "categoryColors": {
    "Active": "#7A9E7E",
    "Inactive": "#BC6C25",
    "Pending": "#D4A27F",
    "Completed": "#3C6E71",
    "Cancelled": "#E8734A"
  },
  "layoutRules": {
    "gap": 20,
    "margin": 20,
    "preventOverlaps": true,
    "dimensionSnap": 8
  },
  "typography": {
    "fontFamily": "Segoe UI",
    "elements": {
      "pageTitle": { "size": 24, "weight": "bold", "color": "#1A1A2E" },
      "visualTitle": { "size": 12, "weight": "semibold" },
      "kpiValues": { "size": 28, "weight": "bold", "color": "#E8734A" }
    }
  },
  "colors": {
    "sentiment": {
      "positive": "#7A9E7E",
      "negative": "#E8734A",
      "neutral": "#C9CBA3"
    },
    "divergent": {
      "max": "#3C6E71",
      "middle": "#F2E8CF",
      "min": "#E8734A"
    }
  },
  "rules": {
    "titlePattern": "^[A-Z][A-Za-z0-9 ]+$",
    "approvedFonts": ["Segoe UI", "DIN", "Arial"]
  }
}
```

## Bundled Style Guides

| File | Description |
|---|---|
| `examples/style_guide.example.json` | Blank template with default Power BI colors; copy and customise with your brand |
| `examples/style_guide.enterprise.json` | MB OneData corporate style guide — full typography, three-tier color palette, page structure zones, visual type rules for 11 visual types |

Use `get_default_style_guide()` to see which guide is currently active, and `set_default_style_guide(style_guide)` to change it at runtime.
