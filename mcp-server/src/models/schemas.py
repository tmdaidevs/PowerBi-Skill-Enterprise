from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    BLOCKER = "blocker"


class ReportFormat(str, Enum):
    PBIR = "PBIR"
    PBIR_LEGACY = "PBIR-Legacy"
    UNKNOWN = "Unknown"


class MCPErrorCode(str, Enum):
    UNSUPPORTED_REPORT_FORMAT = "unsupported_report_format"
    EXTERNAL_EDITING_NOT_SUPPORTED = "external_editing_not_supported"
    VALIDATION_FAILED = "validation_failed"
    THROTTLED_RETRYABLE = "throttled_retryable"
    ASYNC_OPERATION_PENDING = "async_operation_pending"
    CORRUPTED_PAYLOAD_RISK = "corrupted_payload_risk"
    TRANSIENT_UPSTREAM_FAILURE = "transient_upstream_failure"
    AUTH_FAILED = "auth_failed"
    FORBIDDEN_SCOPE = "forbidden_scope"


class WarningItem(BaseModel):
    severity: Severity
    code: str
    message: str
    remediation: str | None = None


class ToolResponse(BaseModel):
    success: bool
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
    warnings: list[WarningItem] = Field(default_factory=list)
    blockers: list[WarningItem] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class ReportPart(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    path: str
    content_type: str
    payload: dict[str, Any] | list[Any] | str
    payload_type: str | None = None  # "InlineBase64" or None — needed for re-encoding on writeback


class VisualDefinition(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    name: str | None = None
    visual_type: str
    page_id: str
    x: float | None = None
    y: float | None = None
    width: float | None = None
    height: float | None = None
    z_order: int | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    objects: dict[str, Any] = Field(default_factory=dict)  # visual-level formatting (data colors, axes)
    raw: dict[str, Any] = Field(default_factory=dict)


class PageDefinition(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    display_name: str | None = None
    order: int = 0
    visuals: list[VisualDefinition] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)


class BookmarkDefinition(BaseModel):
    id: str
    name: str
    raw: dict[str, Any] = Field(default_factory=dict)


class StaticResource(BaseModel):
    name: str
    resource_type: str
    raw: dict[str, Any] = Field(default_factory=dict)


class ReportDefinition(BaseModel):
    model_config = ConfigDict(extra="allow")

    report_id: str
    workspace_id: str
    format: ReportFormat = ReportFormat.UNKNOWN
    metadata: dict[str, Any] = Field(default_factory=dict)
    parts: list[ReportPart] = Field(default_factory=list)
    pages: list[PageDefinition] = Field(default_factory=list)
    bookmarks: list[BookmarkDefinition] = Field(default_factory=list)
    static_resources: list[StaticResource] = Field(default_factory=list)
    unsupported_artifacts: list[str] = Field(default_factory=list)


class StyleGuideTheme(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    primary_color: str = Field(alias="primaryColor")
    background_color: str = Field(alias="backgroundColor")
    text_color: str = Field(alias="textColor")
    data_colors: list[str] = Field(default_factory=list, alias="dataColors")


# ---------------------------------------------------------------------------
# Typography — extended with per-element font specs
# ---------------------------------------------------------------------------

class FontSpec(BaseModel):
    """Font specification for a single UI element type."""
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    size: int = Field(ge=6, le=72)
    weight: str = Field(default="Regular")  # "Regular", "Bold", "SemiBold", "Light"
    color: str | None = None  # optional override; falls back to theme textColor


class StyleGuideTypography(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    title_font_family: str = Field(alias="titleFontFamily")
    body_font_family: str = Field(alias="bodyFontFamily")
    title_font_size: int = Field(alias="titleFontSize", ge=8, le=72)
    body_font_size: int = Field(alias="bodyFontSize", ge=6, le=48)
    # Extended: single font family override for the entire report
    font_family: str | None = Field(default=None, alias="fontFamily")
    # Extended: per-element font specs (pageTitle, subtitle, visualTitle, etc.)
    elements: dict[str, FontSpec] | None = None


# ---------------------------------------------------------------------------
# Colors — multi-tier palette, sentiment, divergent, theme advanced
# ---------------------------------------------------------------------------

class ColorEntry(BaseModel):
    """A named color with optional design-token and usage description."""
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    name: str
    hex: str
    token: str | None = None
    usage: str | None = None


class SentimentColors(BaseModel):
    """Semantic colors for positive/negative/neutral indicators."""
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    positive: str = "#198025"
    negative: str = "#D92121"
    neutral: str = "#E8BD00"


class DivergentColors(BaseModel):
    """Min-middle-max gradient colors for divergent analysis."""
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    max: str
    middle: str
    min: str


class ThemeAdvancedColors(BaseModel):
    """Maps to Power BI theme advanced element color categories."""
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    first_level: str | None = Field(default=None, alias="firstLevel")
    second_level: str | None = Field(default=None, alias="secondLevel")
    third_level: str | None = Field(default=None, alias="thirdLevel")
    fourth_level: str | None = Field(default=None, alias="fourthLevel")
    background: str | None = None
    secondary_background: str | None = Field(default=None, alias="secondaryBackground")


class StyleGuideColors(BaseModel):
    """Extended color configuration supporting tiered palettes and semantic colors."""
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    # Tiered report UI colors (backgrounds, text, icons)
    report_palette: dict[str, list[ColorEntry]] | None = Field(default=None, alias="reportPalette")
    # Ordered data colors for chart series (replaces theme.dataColors when present)
    visual_palette: list[ColorEntry] | None = Field(default=None, alias="visualPalette")
    # Semantic indicator colors
    sentiment: SentimentColors | None = None
    # Divergent analysis gradient
    divergent: DivergentColors | None = None
    # PBI theme advanced element colors
    theme_advanced: ThemeAdvancedColors | None = Field(default=None, alias="themeAdvanced")
    # Dimension-value → color mapping (promoted from top-level)
    category_colors: dict[str, str] | None = Field(default=None, alias="categoryColors")


# ---------------------------------------------------------------------------
# Page structure — zones with pixel-precise layout
# ---------------------------------------------------------------------------

class ImagePlacement(BaseModel):
    """Position and size for an image element within a zone."""
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    url: str | None = None
    width: int
    height: int
    x: int
    y: int
    name: str | None = None


class CanvasSize(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    width: int = 1280
    height: int = 720


class HeaderZone(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    height: int = 64
    background_color: str | None = Field(default=None, alias="backgroundColor")
    elements: dict[str, ImagePlacement] | None = None


class FooterZone(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    height: int = 32
    background_color: str | None = Field(default=None, alias="backgroundColor")
    elements: dict[str, ImagePlacement] | None = None
    navigation_items: list[str] | None = Field(default=None, alias="navigationItems")


class FilterPanelZone(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    side: str = "right"  # "right" or "left"
    width: int = 200
    top_padding: int = Field(default=18, alias="topPadding")
    background_color: str | None = Field(default=None, alias="backgroundColor")


class BodyZone(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    left_margin: int = Field(default=40, alias="leftMargin")
    right_margin: int = Field(default=24, alias="rightMargin")
    top_margin: int = Field(default=32, alias="topMargin")
    bottom_margin: int = Field(default=16, alias="bottomMargin")
    inner_padding: int = Field(default=24, alias="innerPadding")
    inter_visual_gap: int = Field(default=24, alias="interVisualGap")


class PageStructure(BaseModel):
    """Defines the zone-based page layout (header, footer, filter, body)."""
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    canvas: CanvasSize | None = None
    header: HeaderZone | None = None
    footer: FooterZone | None = None
    filter_panel: FilterPanelZone | None = Field(default=None, alias="filterPanel")
    body: BodyZone | None = None


# ---------------------------------------------------------------------------
# Visual element styles — deep per-element formatting
# ---------------------------------------------------------------------------

class VisualElementStyle(BaseModel):
    """Formatting spec for a single visual element (header, values, axis, etc.)."""
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    bg_color: str | list[str] | None = Field(default=None, alias="bgColor")  # list for alternating rows
    font_size: int | None = Field(default=None, alias="fontSize")
    font_weight: str | None = Field(default=None, alias="fontWeight")
    font_color: str | None = Field(default=None, alias="fontColor")
    position: str | None = None  # e.g. "TopLeft" for legend


class VisualTypeRules(BaseModel):
    """Deep formatting rules for a specific visual type."""
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    # Table/Matrix elements
    header: VisualElementStyle | None = None
    values: VisualElementStyle | None = None
    total: VisualElementStyle | None = None
    # Chart axis elements
    x_axis: VisualElementStyle | None = Field(default=None, alias="xAxis")
    y_axis: VisualElementStyle | None = Field(default=None, alias="yAxis")
    # Legend
    legend: VisualElementStyle | None = None
    # Data labels
    labels: VisualElementStyle | None = None
    # Table variant support (e.g. "v1" dark header, "v2" light header)
    variants: dict[str, dict[str, VisualElementStyle]] | None = None
    default_variant: str | None = Field(default=None, alias="defaultVariant")
    # Legacy flat rules (backward compat)
    extra: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Layout — extended with dimension snapping
# ---------------------------------------------------------------------------

class StyleGuideLayout(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    page_padding: int = Field(alias="pagePadding", ge=0, le=200)
    visual_spacing: int = Field(alias="visualSpacing", ge=0, le=200)
    corner_radius: int = Field(alias="cornerRadius", ge=0, le=100)
    # Extended: snap all dimensions to multiples of this value (e.g. 4 or 8)
    dimension_snap: int | None = Field(default=None, alias="dimensionSnap", ge=1, le=64)


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

class StyleGuideRules(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    max_visuals_per_page: int = Field(alias="maxVisualsPerPage", ge=1, le=100)
    allow_custom_visuals: bool = Field(alias="allowCustomVisuals", default=True)
    enforce_top_row_kpis: bool = Field(alias="enforceTopRowKpis", default=False)
    # Extended: optional regex pattern for visual title validation
    title_pattern: str | None = Field(default=None, alias="titlePattern")
    # Extended: approved font families (validator checks compliance)
    approved_fonts: list[str] | None = Field(default=None, alias="approvedFonts")


# ---------------------------------------------------------------------------
# StyleGuide — top-level model with all optional extensions
# ---------------------------------------------------------------------------

class PageStyleOverride(BaseModel):
    """Per-page overrides for style guide settings."""
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    visual_type_rules: dict[str, VisualTypeRules] | None = Field(default=None, alias="visualTypeRules")
    body: BodyZone | None = None
    background_color: str | None = Field(default=None, alias="backgroundColor")


class StyleGuide(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    theme: StyleGuideTheme
    typography: StyleGuideTypography
    layout: StyleGuideLayout
    rules: StyleGuideRules
    # Legacy flat visual rules (backward compat)
    visual_rules: dict[str, dict[str, Any]] = Field(default_factory=dict, alias="visualRules")
    # Extended: structured per-visual-type formatting
    visual_type_rules: dict[str, VisualTypeRules] | None = Field(default=None, alias="visualTypeRules")
    # Extended: multi-tier color system
    colors: StyleGuideColors | None = None
    # Extended: zone-based page layout
    page_structure: PageStructure | None = Field(default=None, alias="pageStructure")
    # Extended: top-level category colors (legacy location, also in colors.categoryColors)
    category_colors: dict[str, str] | None = Field(default=None, alias="categoryColors")
    # Extended: per-page overrides keyed by page name
    page_overrides: dict[str, PageStyleOverride] | None = Field(default=None, alias="pageOverrides")

    def get_data_colors(self) -> list[str]:
        """Resolve the effective data color palette (visual palette > theme.dataColors)."""
        if self.colors and self.colors.visual_palette:
            return [c.hex for c in self.colors.visual_palette]
        return self.theme.data_colors

    def get_category_colors(self) -> dict[str, str]:
        """Resolve category colors from either location."""
        if self.colors and self.colors.category_colors:
            return self.colors.category_colors
        return self.category_colors or {}

    def get_font_family(self) -> str:
        """Resolve the primary font family."""
        if self.typography.font_family:
            return self.typography.font_family
        return self.typography.title_font_family

    def get_dimension_snap(self) -> int | None:
        """Return the dimension snap value if set."""
        return self.layout.dimension_snap


class TransformationChange(BaseModel):
    target: str
    path: str
    old_value: Any
    new_value: Any
    risk_note: str | None = None


class TransformationPlan(BaseModel):
    report_id: str
    workspace_id: str
    dry_run: bool = True
    changes: list[TransformationChange] = Field(default_factory=list)
    warnings: list[WarningItem] = Field(default_factory=list)


class ValidationResult(BaseModel):
    valid: bool
    issues: list[WarningItem] = Field(default_factory=list)


class DiffEntry(BaseModel):
    path: str
    before: Any
    after: Any


class DiffResult(BaseModel):
    changed_parts: list[str] = Field(default_factory=list)
    field_changes: list[DiffEntry] = Field(default_factory=list)
    summary: str


class LayoutConfig(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    margin: int = Field(default=20, alias="margin", ge=0, le=200)
    gap: int = Field(default=20, alias="gap", ge=0, le=200)
    page_width: int = Field(default=1280, alias="pageWidth")
    auto_height: bool = Field(default=True, alias="autoHeight")


class ModernizationScore(BaseModel):
    score: int = Field(ge=0, le=100)
    classification: str
    reasons: list[str]
    suggested_next_action: str
