# Power BI Creator Skill — Enterprise Edition

A [GitHub Copilot CLI](https://githubnext.com/projects/copilot-cli/) skill for creating, designing, and managing Power BI reports and semantic models. Combines two MCP servers:

- **Power BI Design MCP Server** (included) — PBIR report styling, visuals, themes, layout
- **[Power BI Modeling MCP Server](https://github.com/microsoft/powerbi-modeling-mcp)** (Microsoft, via npx) — Semantic model authoring, tables, measures, DAX, relationships

## Features

- **36 MCP tools** spanning discovery, styling, visual CRUD, page management, validation, persistence, and governance
- **Extended style guide system** — typography, multi-tier color palettes, page structure zones, deep per-visual formatting rules, dimension snapping, and style compliance validation
- **Custom visual development** — scaffold, build, and package D3.js Power BI custom visuals with `pbiviz` SDK (template included)
- **Auto theme injection** — data colors, sentiment colors, divergent colors, advanced element colors, and font families are injected into the Power BI custom theme
- **Page structure zones** — header, footer, filter panel, and body zones with pixel-precise element positioning
- **Per-visual-type formatting** — table header/values/totals, chart axes/legend, KPI cards, gauges, donut charts — all configurable per visual type with variant support
- **Conditional formatting** via `FillRule` + `linearGradient2` with `dataViewWildcard` selectors — default colors from style guide sentiment palette
- **Overlap & gap validation** — layout rules enforce configurable gaps/margins; overlapping visuals are blocked before they reach Fabric
- **Dimension snapping** — enforce all visual positions and sizes as multiples of 4 or 8 pixels
- **Style compliance validation** — pre-publish checklist for fonts, colors, spacing, zone boundaries, and title patterns
- **Automatic backups** — every write operation snapshots the prior definition; full rollback support
- **Audit logging** — every mutation is recorded with timestamp, tool, workspace, and report IDs
- **Bulk governance** — apply a style guide across multiple reports in one call
- **Dry-run mode** — preview every change before committing

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/tmdaidevs/PowerBi-Skill-Enterprise.git
cd PowerBi-Skill-Enterprise
```

### 2. Create a Python virtual environment

```bash
cd mcp-server
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -e ".[dev]"
```

### 4. Configure authentication

Copy the example env file and fill in your credentials:

```bash
cp examples/.env.example .env
```

Edit `.env` with your Azure / Fabric credentials (see [Authentication](#authentication) below).

### 5. Set your style guide (optional)

Point the server at your brand's style guide JSON:

```bash
# In .env
PBIR_MCP_DEFAULT_STYLE_GUIDE_PATH=/path/to/your/style_guide.json
```

Or set it at runtime:

```python
set_default_style_guide(your_style_guide_dict)
```

### 6. Register the skill in Copilot CLI

Copy or symlink the skill and MCP config into your Copilot CLI skills directory, or point Copilot CLI at this repo's `skill/` folder.

```
skill/powerbi-creator.skill.md   → skill definition
skill/mcp.json                   → MCP server configuration
```

## Authentication

The MCP server authenticates against the Fabric REST API. Three modes are supported:

| Mode | Env vars | When to use |
|---|---|---|
| **Service Principal** | `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` | CI / automation |
| **Managed Identity** | (none — uses `DefaultAzureCredential`) | Azure-hosted agents |
| **Delegated / Device-code** | `AZURE_TENANT_ID` | Local development |

All modes require the `https://analysis.windows.net/powerbi/api/.default` scope.

---

## Style Guide System

The extended style guide is the core of the Enterprise Edition. It defines every aspect of how reports look — colors, fonts, layout zones, and per-visual formatting — in a single JSON file.

### Where to Find the Templates

The repo ships with **two template files** in `mcp-server/examples/`:

```
mcp-server/
└── examples/
    ├── style_guide.example.json        ← Blank template (all sections shown, neutral defaults)
    └── style_guide.enterprise.json     ← Full-featured example with all sections populated
```

| File | What it is | Use it when |
|---|---|---|
| [`style_guide.example.json`](mcp-server/examples/style_guide.example.json) | Blank template with placeholder values and all schema sections visible | Starting from scratch — copy and fill in your brand values |
| [`style_guide.enterprise.json`](mcp-server/examples/style_guide.enterprise.json) | Complete working example with page zones, 11 visual type rules, sentiment colors, etc. | Reference for what a fully-configured guide looks like |

> **Tip:** Open `style_guide.enterprise.json` side-by-side with your brand guidelines — it shows every field you can configure.

### Style Guide Overview

| Section | What it controls | Required? |
|---|---|---|
| `theme` | Primary color, background, text color, data colors palette | ✅ Yes |
| `typography` | Font family, per-element font sizes and weights (9 element types) | ✅ Yes |
| `layout` | Spacing, padding, corner radius, dimension snapping | ✅ Yes |
| `rules` | Max visuals per page, approved fonts, title patterns | ✅ Yes |
| `colors` | Multi-tier color palette, sentiment colors, divergent colors | Optional |
| `pageStructure` | Header/footer/filter panel/body zones with pixel-precise positioning | Optional |
| `visualTypeRules` | Per-visual formatting for 13 visual types with variant support | Optional |
| `pageOverrides` | Per-page overrides (different rules for specific pages) | Optional |
| `categoryColors` | Dimension-value → color mapping (e.g., "Active" → green) | Optional |

### Tutorial: Creating Your Style Guide

#### Step 1: Copy the template

From the repo root:

```bash
# Copy the blank template
cp mcp-server/examples/style_guide.example.json my_brand_guide.json

# Or start from the full enterprise example and modify it
cp mcp-server/examples/style_guide.enterprise.json my_brand_guide.json
```

Your file can live **anywhere** — you'll point the server at it in Step 8.

#### Step 2: Set your brand colors

Open `my_brand_guide.json` and edit the `theme` section with your brand's primary palette:

```json
{
  "theme": {
    "primaryColor": "#0078D4",
    "backgroundColor": "#F5F5F5",
    "textColor": "#1A1A1A",
    "dataColors": ["#0078D4", "#2B88D8", "#71AFE5", "#C7E0F4"]
  }
}
```

- `primaryColor` — your main brand color (used for links, accents, table accent)
- `backgroundColor` — default page background
- `textColor` — default text color
- `dataColors` — ordered palette for chart series (injected as a Power BI custom theme)
```

#### Step 3: Set your typography

Define your approved font and per-element sizes:

```json
{
  "typography": {
    "titleFontFamily": "Segoe UI Semibold",
    "bodyFontFamily": "Segoe UI",
    "titleFontSize": 24,
    "bodyFontSize": 10,
    "fontFamily": "Your Brand Font",
    "elements": {
      "pageTitle":    { "size": 24, "weight": "Regular" },
      "subtitle":     { "size": 9,  "weight": "Regular" },
      "visualTitle":  { "size": 18, "weight": "Bold" },
      "filterBarTitle": { "size": 12, "weight": "Regular" },
      "axisLabels":   { "size": 10, "weight": "Regular" },
      "filterValues": { "size": 8,  "weight": "Regular" },
      "tableHeaders": { "size": 10, "weight": "Bold" },
      "tableTotals":  { "size": 12, "weight": "Bold" },
      "kpiValues":    { "size": 15, "weight": "Regular" }
    }
  }
}
```

#### Step 4: Add multi-tier colors (optional)

Define report UI colors, visual data colors, and semantic indicator colors:

```json
{
  "colors": {
    "reportPalette": {
      "primary": [
        { "name": "White",   "hex": "#FFFFFF", "usage": "Backgrounds" },
        { "name": "Black",   "hex": "#1A1A1A", "usage": "Main text" },
        { "name": "Brand",   "hex": "#0078D4", "usage": "Links, accents" }
      ],
      "secondary": [
        { "name": "Light BG", "hex": "#F5F5F5", "usage": "Page background" }
      ]
    },
    "visualPalette": [
      { "name": "Blue 1", "hex": "#0078D4" },
      { "name": "Blue 2", "hex": "#2B88D8" },
      { "name": "Blue 3", "hex": "#71AFE5" }
    ],
    "sentiment": {
      "positive": "#107C10",
      "negative": "#D13438",
      "neutral":  "#CA5010"
    },
    "divergent": {
      "max":    "#004578",
      "middle": "#2B88D8",
      "min":    "#C7E0F4"
    }
  }
}
```

#### Step 5: Define page structure zones (optional)

Set up header, footer, filter panel, and body zones:

```json
{
  "pageStructure": {
    "canvas": { "width": 1280, "height": 720 },
    "header": {
      "height": 64,
      "backgroundColor": "#1A1A1A",
      "elements": {
        "logoLeft":  { "width": 40, "height": 40, "x": 16,   "y": 12, "name": "Company Logo" },
        "logoRight": { "width": 64, "height": 32, "x": 1200, "y": 16, "name": "Product Logo" }
      }
    },
    "footer": {
      "height": 32,
      "navigationItems": ["Home", "Details", "FAQ", "Help"]
    },
    "filterPanel": { "side": "right", "width": 200 },
    "body": {
      "leftMargin": 40, "rightMargin": 24,
      "topMargin": 32,  "bottomMargin": 16,
      "innerPadding": 24, "interVisualGap": 24
    }
  }
}
```

#### Step 6: Define visual formatting rules (optional)

Set per-visual-type formatting for tables, charts, KPI cards, etc.:

```json
{
  "visualTypeRules": {
    "table": {
      "variants": {
        "v1": {
          "header": { "bgColor": "#333333", "fontSize": 10, "fontWeight": "Bold", "fontColor": "#FFFFFF" },
          "values": { "bgColor": ["#F5F5F5", "#FFFFFF"], "fontSize": 10, "fontColor": "#1A1A1A" },
          "total":  { "bgColor": "#FFFFFF", "fontSize": 12, "fontColor": "#333333" }
        },
        "v2": {
          "header": { "bgColor": "#FFFFFF", "fontSize": 10, "fontWeight": "Bold", "fontColor": "#333333" },
          "values": { "bgColor": ["#F5F5F5", "#FFFFFF"], "fontSize": 10, "fontColor": "#1A1A1A" },
          "total":  { "bgColor": "#333333", "fontSize": 12, "fontColor": "#FFFFFF" }
        }
      },
      "defaultVariant": "v1"
    },
    "lineChart": {
      "xAxis":  { "fontSize": 10, "fontColor": "#1A1A1A" },
      "yAxis":  { "fontSize": 10, "fontColor": "#1A1A1A" },
      "legend": { "position": "TopLeft", "fontSize": 10, "fontColor": "#1A1A1A" }
    },
    "kpiCard": {
      "labels": { "fontSize": 15, "fontColor": "#1A1A1A" }
    }
  }
}
```

#### Step 7: Set layout constraints (optional)

```json
{
  "layout": {
    "pagePadding": 16,
    "visualSpacing": 24,
    "cornerRadius": 0,
    "dimensionSnap": 4
  },
  "rules": {
    "maxVisualsPerPage": 6,
    "approvedFonts": ["Your Brand Font"],
    "titlePattern": "^[A-Z].*"
  }
}
```

#### Step 8: Activate your style guide

There are three ways to point the server at your style guide:

**Option A: Environment variable (recommended for production)**

Add to your `.env` file in `mcp-server/`:

```bash
# .env
PBIR_MCP_DEFAULT_STYLE_GUIDE_PATH=/absolute/path/to/my_brand_guide.json
```

Or use a relative path from where you start the server:

```bash
PBIR_MCP_DEFAULT_STYLE_GUIDE_PATH=./my_brand_guide.json
```

**Option B: Runtime API call (recommended for testing)**

Call the MCP tool at any time to load a style guide:

```
set_default_style_guide({...your style guide JSON...})
```

This saves the guide to `mcp-server/examples/style_guide.default.json` and uses it for all subsequent operations.

**Option C: Pass directly to each tool call**

Every styling tool accepts an optional `style_guide` parameter:

```
apply_style_guide(workspace_id, report_id, style_guide={...}, dry_run=true)
migrate_report(workspace_id, report_id, target_style_guide={...}, dry_run=true)
```

#### How it gets applied automatically

Once a default style guide is set (Option A or B), it's automatically applied during:

| Operation | What happens |
|---|---|
| `add_visual_to_page` | Style guide applied after visual is created |
| `add_page` / `build_page` | Style guide applied after page is created |
| `apply_full_style` | Loads default guide and applies everything in one pass |
| `full_modernization` | Applies guide + page structure + validates compliance |
| `migrate_report` | Full migration: extract → diff → apply → validate |
| `rearrange_page_visuals` | Re-applies style after layout changes |
| `restore_report_definition` | Re-applies style after restoring from backup |

### Migrating an Existing Report

To migrate an existing report to your style guide:

```
# Preview what will change (dry run)
migrate_report(workspace_id, report_id, dry_run=true)

# Execute the migration
migrate_report(workspace_id, report_id, dry_run=false)
```

The migration tool automatically:
1. Extracts the report's current styling
2. Diffs it against your target style guide
3. Backs up the report
4. Applies the style guide (colors, typography, visual rules)
5. Applies page structure (header/footer/filter zones, logos)
6. Rearranges visuals to fix spacing
7. Validates compliance and returns a before/after report

### Extracting a Style Guide from an Existing Report

Don't have a style guide yet? Extract one from an existing report:

```
extract_style_guide_from_report(workspace_id, report_id)
```

This reverse-engineers the report's current styling into a style guide JSON, including:
- Font families and per-element sizes
- Data colors from the theme
- Sentiment and divergent colors
- Per-visual formatting rules (table headers, chart axes, legend settings)

The response includes `extendedFieldsExtracted` showing what was auto-detected. You'll need to manually add `pageStructure` and `categoryColors` since those can't be inferred from visuals alone.

### Comparing Two Style Guides

To see what differs between your current and target style guides:

```
diff_style_guides(guide_a={...current...}, guide_b={...target...})
```

Returns categorized changes: colors, typography, layout, rules, visual type rules, page structure.

Review the extracted guide, add `pageStructure` and `categoryColors` manually, then use it as your default.

### Validating Style Compliance

Before publishing, run the compliance check:

```
validate_style_compliance(workspace_id, report_id)
```

This checks:
- ✅ **Font compliance** — all visuals use approved font families
- ✅ **Color compliance** — explicit colors are in the approved palette
- ✅ **Dimension snapping** — x/y/width/height are multiples of the snap value
- ✅ **Zone compliance** — visuals are within body zone boundaries
- ✅ **Title consistency** — visual names match the naming pattern

---

## Architecture

The MCP server is organised into seven layers:

1. **Auth** (`src/auth/`) — token acquisition via `azure-identity`
2. **Fabric Client** (`src/fabric_client/`) — REST calls to the Fabric / Power BI API
3. **Parser** (`src/parser/`) — PBIR definition decoding, page/visual extraction
4. **Transformations** (`src/transformations/`) — style application, theme building, page structure, conditional formatting
5. **Validation** (`src/validation/`) — overlap detection, gap enforcement, font/color/zone compliance
6. **MCP Tools** (`src/mcp_tools/`) — thin tool wrappers exposed over the MCP protocol
7. **Config** (`src/config/`) — settings, env vars, default style guide path

## Project Layout

```
PowerBi-Skill-Enterprise/
├── README.md
├── LICENSE
├── .gitignore
├── mcp-server/                    ← Power BI Design MCP Server
│   ├── src/
│   │   ├── auth/                  ← Azure authentication
│   │   ├── config/                ← Settings & env vars
│   │   ├── fabric_client/         ← Fabric REST API client
│   │   ├── mcp_tools/             ← MCP tool endpoints
│   │   ├── models/                ← Pydantic schemas (StyleGuide, etc.)
│   │   ├── parser/                ← PBIR definition parser
│   │   ├── server/                ← Service layer & MCP server
│   │   ├── transformations/       ← Style engine, theme builder, page structure
│   │   ├── utils/                 ← Scoring utilities
│   │   └── validation/            ← Report & style compliance validator
│   ├── tests/
│   ├── examples/
│   │   ├── style_guide.example.json      ← Blank template
│   │   └── style_guide.enterprise.json   ← Full-featured example
│   └── pyproject.toml
├── skill/
│   ├── powerbi-creator.skill.md   ← Copilot CLI skill definition
│   └── mcp.json                   ← MCP server config template
├── custom-visual-template/        ← pbiviz custom visual scaffold
└── docs/
    ├── setup.md
    └── style-guide.md             ← Full style guide schema reference
```

## MCP Tools Reference

### Discovery
- `list_workspaces()` — List all accessible workspaces
- `list_reports(workspace_id)` — List reports in a workspace
- `get_report_metadata(workspace_id, report_id)` — Get report details
- `analyze_report_structure(workspace_id, report_id)` — Analyze pages, visuals, bookmarks

### Styling & Theming
- `apply_style_guide(workspace_id, report_id, style_guide, dry_run)` — Apply a style guide
- `apply_full_style(workspace_id, report_id, dry_run)` — Auto-loads default style guide
- `apply_page_structure(workspace_id, report_id, style_guide, dry_run)` — Apply zone-based page layout
- `inject_custom_theme(workspace_id, report_id, theme_json, dry_run)` — Inject a PBI custom theme
- `apply_conditional_format(workspace_id, report_id, page, visual, column, rules, dry_run)` — Conditional formatting

### Visual & Page CRUD
- `add_visual_to_page` / `add_image_visual` / `build_page` / `add_page`
- `patch_visual_properties` / `patch_page_properties` / `patch_report_properties`
- `remove_visual` / `remove_page` / `rename_visual` / `reorder_pages`
- `rearrange_page_visuals` — Fix spacing and overlaps

### Validation
- `validate_report_definition(workspace_id, report_id)` — Structural validation
- `validate_style_compliance(workspace_id, report_id)` — Full style guide compliance check
- `score_modernization_readiness(workspace_id, report_id)` — PBIR readiness score

### Governance
- `bulk_apply_style_guide(workspace_id, report_ids, style_guide, dry_run)` — Bulk enforcement
- `extract_style_guide_from_report(workspace_id, report_id)` — Reverse-engineer a style guide
- `get_default_style_guide()` / `set_default_style_guide(style_guide)` — Manage default
- `get_audit_log()` — Operation history
- `full_modernization(workspace_id, report_id, confirm)` — Complete report migration

### Safety
- `backup_report_definition` / `list_backups` / `restore_report_definition`
- `preview_changes` / `diff_report_definition`
- All writes use `dry_run=true` by default

## License

[MIT](LICENSE) © 2026 tmdaidevs
