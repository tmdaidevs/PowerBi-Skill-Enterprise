"""Tests for the extended style guide features: typography, colors, page structure,
grid snapping, deep visual rules, theme builder, and enhanced validation."""

from src.models.schemas import (
    BodyZone,
    CanvasSize,
    ColorEntry,
    DivergentColors,
    FilterPanelZone,
    FontSpec,
    FooterZone,
    HeaderZone,
    ImagePlacement,
    PageDefinition,
    PageStructure,
    ReportDefinition,
    ReportFormat,
    SentimentColors,
    StyleGuide,
    StyleGuideColors,
    ThemeAdvancedColors,
    VisualDefinition,
    VisualElementStyle,
    VisualTypeRules,
)
from src.transformations.style_engine import StyleTransformationEngine, _resolve_font_weight
from src.transformations.theme_builder import ThemeBuilder
from src.transformations.page_structure import PageStructureEngine
from src.validation.validator import ReportValidator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_guide(**overrides) -> StyleGuide:
    data = {
        "theme": {"primaryColor": "#0078D6", "backgroundColor": "#F8F8F8", "textColor": "#000000"},
        "typography": {
            "titleFontFamily": "Segoe UI Semibold",
            "bodyFontFamily": "Segoe UI",
            "titleFontSize": 16,
            "bodyFontSize": 10,
        },
        "layout": {"pagePadding": 16, "visualSpacing": 12, "cornerRadius": 0},
        "rules": {"maxVisualsPerPage": 6, "allowCustomVisuals": True, "enforceTopRowKpis": False},
    }
    data.update(overrides)
    return StyleGuide.model_validate(data)


def _report_with_visual(visual_type: str = "barChart", x=100, y=100, w=200, h=200) -> ReportDefinition:
    return ReportDefinition(
        report_id="r1",
        workspace_id="w1",
        format=ReportFormat.PBIR,
        parts=[],
        pages=[
            PageDefinition(
                id="p1",
                name="Page1",
                visuals=[
                    VisualDefinition(
                        id="v1",
                        name="TestVisual",
                        visual_type=visual_type,
                        page_id="p1",
                        x=x, y=y, width=w, height=h,
                        properties={},
                        objects={},
                        raw={},
                    )
                ],
            )
        ],
    )


# ---------------------------------------------------------------------------
# Schema backward compatibility
# ---------------------------------------------------------------------------

class TestSchemaBackwardCompat:
    def test_legacy_guide_parses(self):
        guide = _base_guide()
        assert guide.theme.primary_color == "#0078D6"
        assert guide.colors is None
        assert guide.page_structure is None
        assert guide.visual_type_rules is None

    def test_get_data_colors_fallback(self):
        guide = _base_guide()
        guide.theme.data_colors = ["#AAA", "#BBB"]
        assert guide.get_data_colors() == ["#AAA", "#BBB"]

    def test_get_data_colors_prefers_visual_palette(self):
        guide = _base_guide(
            colors={
                "visualPalette": [
                    {"name": "Blue", "hex": "#0078D6"},
                    {"name": "Red", "hex": "#FF0000"},
                ]
            }
        )
        assert guide.get_data_colors() == ["#0078D6", "#FF0000"]

    def test_get_font_family(self):
        guide = _base_guide()
        assert guide.get_font_family() == "Segoe UI Semibold"  # falls back to title font

        guide2 = _base_guide(typography={
            "titleFontFamily": "Segoe UI",
            "bodyFontFamily": "Segoe UI",
            "titleFontSize": 14,
            "bodyFontSize": 10,
            "fontFamily": "Custom Brand Font",
        })
        assert guide2.get_font_family() == "Custom Brand Font"


# ---------------------------------------------------------------------------
# Font weight mapping
# ---------------------------------------------------------------------------

class TestFontWeight:
    def test_regular(self):
        assert _resolve_font_weight("Regular") == 400

    def test_bold(self):
        assert _resolve_font_weight("Bold") == 700

    def test_semibold(self):
        assert _resolve_font_weight("SemiBold") == 600

    def test_unknown_defaults_400(self):
        assert _resolve_font_weight("CustomWeight") == 400


# ---------------------------------------------------------------------------
# ThemeBuilder
# ---------------------------------------------------------------------------

class TestThemeBuilder:
    def test_basic_theme(self):
        guide = _base_guide()
        theme = ThemeBuilder.build(guide)
        assert theme["name"] == "StyleGuideTheme"
        assert theme["foreground"] == "#000000"
        assert theme["background"] == "#F8F8F8"
        assert theme["tableAccent"] == "#0078D6"

    def test_sentiment_colors(self):
        guide = _base_guide(colors={
            "sentiment": {"positive": "#198025", "negative": "#D92121", "neutral": "#E8BD00"}
        })
        theme = ThemeBuilder.build(guide)
        assert theme["sentimentColors"]["good"] == "#198025"
        assert theme["sentimentColors"]["bad"] == "#D92121"
        assert theme["sentimentColors"]["neutral"] == "#E8BD00"

    def test_divergent_colors(self):
        guide = _base_guide(colors={
            "divergent": {"max": "#025497", "middle": "#008DFC", "min": "#E6F5FF"}
        })
        theme = ThemeBuilder.build(guide)
        assert theme["divergentColors"]["maximum"] == "#025497"
        assert theme["divergentColors"]["center"] == "#008DFC"
        assert theme["divergentColors"]["minimum"] == "#E6F5FF"

    def test_text_classes_with_font_family(self):
        guide = _base_guide(typography={
            "titleFontFamily": "Segoe UI",
            "bodyFontFamily": "Segoe UI",
            "titleFontSize": 14,
            "bodyFontSize": 10,
            "fontFamily": "Custom Brand Font",
        })
        theme = ThemeBuilder.build(guide)
        assert "textClasses" in theme
        assert theme["textClasses"]["callout"]["fontFamily"] == "Custom Brand Font"

    def test_theme_advanced_colors(self):
        guide = _base_guide(colors={
            "themeAdvanced": {
                "firstLevel": "#000000",
                "secondLevel": "#111111",
                "background": "#FFFFFF",
            }
        })
        theme = ThemeBuilder.build(guide)
        assert theme["foregroundNeutralSecondary"] == "#000000"
        assert theme["foregroundNeutralTertiary"] == "#111111"
        assert theme["background"] == "#FFFFFF"


# ---------------------------------------------------------------------------
# PageStructureEngine
# ---------------------------------------------------------------------------

class TestPageStructure:
    def test_compute_body_bounds_default(self):
        structure = PageStructure(
            canvas=CanvasSize(width=1280, height=720),
            header=HeaderZone(height=64),
            footer=FooterZone(height=32),
            filter_panel=FilterPanelZone(side="right", width=200),
            body=BodyZone(left_margin=40, right_margin=24, top_margin=32, bottom_margin=16),
        )
        engine = PageStructureEngine()
        bounds = engine.compute_body_bounds(structure)
        assert bounds["x"] == 40
        assert bounds["y"] == 64 + 32  # header + top margin
        assert bounds["width"] == 1280 - 200 - 40 - 24  # canvas - filter - left - right
        assert bounds["height"] == 720 - 64 - 32 - 32 - 16  # canvas - header - footer - top - bottom

    def test_visual_outside_body_generates_warning(self):
        guide = _base_guide(pageStructure={
            "canvas": {"width": 1280, "height": 720},
            "header": {"height": 64},
            "footer": {"height": 32},
            "filterPanel": {"side": "right", "width": 200},
            "body": {"leftMargin": 40, "topMargin": 32, "bottomMargin": 16, "rightMargin": 24},
        })
        report = _report_with_visual(x=0, y=0, w=100, h=50)  # inside header zone
        engine = PageStructureEngine()
        _, plan = engine.apply_page_structure(report, guide, dry_run=True)
        warning_codes = [w.code for w in plan.warnings]
        assert "visual_outside_body" in warning_codes


# ---------------------------------------------------------------------------
# Validator: style compliance
# ---------------------------------------------------------------------------

class TestValidatorStyleCompliance:
    def test_dimension_snapping(self):
        guide = _base_guide(layout={
            "pagePadding": 16, "visualSpacing": 12, "cornerRadius": 0, "dimensionSnap": 8,
        })
        report = _report_with_visual(x=103, y=100, w=201, h=200)  # 103 and 201 not multiples of 8
        result = ReportValidator().validate_style_compliance(report, guide)
        snap_issues = [i for i in result.issues if i.code == "dimension_not_snapped"]
        assert len(snap_issues) >= 2  # x=103 and w=201

    def test_unapproved_font(self):
        guide = _base_guide(rules={
            "maxVisualsPerPage": 12,
            "allowCustomVisuals": True,
            "enforceTopRowKpis": False,
            "approvedFonts": ["Custom Brand Font"],
        })
        report = _report_with_visual()
        report.pages[0].visuals[0].objects = {"title": {"fontFamily": "Comic Sans MS"}}
        result = ReportValidator().validate_style_compliance(report, guide)
        font_issues = [i for i in result.issues if i.code == "unapproved_font"]
        assert len(font_issues) == 1

    def test_zone_compliance(self):
        guide = _base_guide(pageStructure={
            "canvas": {"width": 1280, "height": 720},
            "header": {"height": 64},
            "footer": {"height": 32},
            "filterPanel": {"side": "right", "width": 200},
            "body": {"leftMargin": 40, "topMargin": 32, "bottomMargin": 16, "rightMargin": 24},
        })
        report = _report_with_visual(x=5, y=5, w=50, h=50)  # in header zone
        result = ReportValidator().validate_style_compliance(report, guide)
        zone_issues = [i for i in result.issues if i.code == "visual_outside_body_zone"]
        assert len(zone_issues) == 1

    def test_title_pattern(self):
        guide = _base_guide(rules={
            "maxVisualsPerPage": 12,
            "allowCustomVisuals": True,
            "enforceTopRowKpis": False,
            "titlePattern": r"^[A-Z].*",
        })
        report = _report_with_visual()
        report.pages[0].visuals[0].name = "lowercase title"
        result = ReportValidator().validate_style_compliance(report, guide)
        title_issues = [i for i in result.issues if i.code == "title_pattern_mismatch"]
        assert len(title_issues) == 1


# ---------------------------------------------------------------------------
# Deep visual type rules
# ---------------------------------------------------------------------------

class TestDeepVisualRules:
    def test_table_header_rules_applied(self):
        guide = _base_guide(visualTypeRules={
            "table": {
                "header": {"bgColor": "#333333", "fontSize": 10, "fontWeight": "Bold", "fontColor": "#FFFFFF"},
            }
        })
        report = _report_with_visual(visual_type="tableEx")
        engine = StyleTransformationEngine()
        _, plan = engine.apply_style_guide(report, guide, dry_run=True)
        # Should have changes for columnHeaders properties
        header_changes = [c for c in plan.changes if "columnHeaders" in c.path]
        assert len(header_changes) > 0

    def test_chart_legend_rules(self):
        guide = _base_guide(visualTypeRules={
            "lineChart": {
                "legend": {"position": "TopLeft", "fontSize": 10, "fontColor": "#000000"},
            }
        })
        report = _report_with_visual(visual_type="lineChart")
        engine = StyleTransformationEngine()
        _, plan = engine.apply_style_guide(report, guide, dry_run=True)
        legend_changes = [c for c in plan.changes if "legend" in c.path]
        assert len(legend_changes) > 0

    def test_table_variant_selection(self):
        guide = _base_guide(visualTypeRules={
            "table": {
                "variants": {
                    "v1": {
                        "header": {"bgColor": "#333333", "fontColor": "#FFFFFF"},
                    },
                    "v2": {
                        "header": {"bgColor": "#FFFFFF", "fontColor": "#333333"},
                    },
                },
                "defaultVariant": "v2",
            }
        })
        report = _report_with_visual(visual_type="tableEx")
        engine = StyleTransformationEngine()
        _, plan = engine.apply_style_guide(report, guide, dry_run=True)
        # v2 header should use white background
        header_bg = [c for c in plan.changes if "backColor" in c.path and "columnHeaders" in c.path]
        assert any(c.new_value == "#FFFFFF" for c in header_bg)
