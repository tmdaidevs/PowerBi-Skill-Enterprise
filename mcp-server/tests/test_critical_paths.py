"""Critical path tests for VCO serialization, rearrange overflow, and sync reliability."""
import json
import pytest

from src.models.schemas import (
    ReportDefinition, ReportPart, StyleGuide,
    PageDefinition, VisualDefinition,
)
from src.transformations.style_engine import StyleTransformationEngine


def _make_report(visuals_data: list[dict], page_width: int = 1280) -> ReportDefinition:
    """Build a minimal ReportDefinition with visuals and matching parts."""
    visuals = []
    parts = []
    for v in visuals_data:
        vid = v["name"]
        visuals.append(VisualDefinition(
            id=vid, name=vid, visual_type=v["type"], page_id="p1",
            x=v.get("x", 0), y=v.get("y", 0),
            width=v.get("w", 300), height=v.get("h", 200),
            objects=v.get("objects", {}),
            raw={"visual": {"visualType": v["type"]}},
        ))
        parts.append(ReportPart(
            name=vid,
            path=f"definition/pages/p1/visuals/{vid}/visual.json",
            content_type="application/json",
            payload_type="InlineBase64",
            payload={
                "name": vid,
                "position": {"x": v.get("x", 0), "y": v.get("y", 0),
                              "width": v.get("w", 300), "height": v.get("h", 200)},
                "visual": {"visualType": v["type"], "objects": v.get("objects", {})},
            },
        ))

    return ReportDefinition(
        report_id="r1", workspace_id="w1", format="PBIR",
        pages=[PageDefinition(id="p1", name="p1", display_name="Page 1", visuals=visuals)],
        parts=parts,
    )


def _enterprise_guide() -> StyleGuide:
    return StyleGuide.model_validate({
        "theme": {"primaryColor": "#0078D4", "backgroundColor": "#FFFFFF", "textColor": "#1F1F1F",
                  "dataColors": ["#0078D4", "#2B88D8"]},
        "typography": {"fontFamily": "Segoe UI", "titleFontFamily": "Segoe UI Semibold",
                       "bodyFontFamily": "Segoe UI", "titleFontSize": 16, "bodyFontSize": 11,
                       "elements": {"visualTitle": {"size": 14, "weight": "Bold", "color": "#1F1F1F"}}},
        "layout": {"pagePadding": 16, "visualSpacing": 24, "cornerRadius": 8, "dimensionSnap": 4},
        "rules": {"maxVisualsPerPage": 10, "allowCustomVisuals": True, "enforceTopRowKpis": True},
    })


class TestVCOSerialization:
    """Verify visualContainerObjects are written in correct PBIR format."""

    def test_vco_border_applied_to_data_visuals(self):
        report = _make_report([
            {"name": "chart1", "type": "clusteredBarChart", "x": 20, "y": 20, "w": 600, "h": 400,
             "objects": {"categoryAxis": [{"properties": {}}]}},
        ])
        guide = _enterprise_guide()
        engine = StyleTransformationEngine()

        result, plan = engine.apply_style_guide(report, guide, dry_run=False)

        # Check VCO in the part payload
        for part in result.parts:
            if part.path.endswith("/visual.json") and isinstance(part.payload, dict):
                vco = part.payload.get("visual", {}).get("visualContainerObjects", {})
                assert "border" in vco, "Border VCO should be set"
                border_props = vco["border"][0]["properties"]
                assert border_props["show"]["expr"]["Literal"]["Value"] == "true"
                assert border_props["radius"]["expr"]["Literal"]["Value"] == "8D"

    def test_vco_not_applied_to_shapes(self):
        report = _make_report([
            {"name": "bg_shape", "type": "shape", "x": 0, "y": 0, "w": 1280, "h": 720},
        ])
        guide = _enterprise_guide()
        engine = StyleTransformationEngine()

        result, plan = engine.apply_style_guide(report, guide, dry_run=False)

        for part in result.parts:
            if part.path.endswith("/visual.json") and isinstance(part.payload, dict):
                vco = part.payload.get("visual", {}).get("visualContainerObjects", {})
                assert "border" not in vco, "Shapes should not get VCO"

    def test_objects_serialized_as_arrays(self):
        """PBIR requires objects as arrays, not flat dicts."""
        report = _make_report([
            {"name": "chart1", "type": "clusteredBarChart", "x": 20, "y": 20, "w": 600, "h": 400,
             "objects": {"categoryAxis": [{"properties": {}}], "title": [{"properties": {}}]}},
        ])
        guide = _enterprise_guide()
        engine = StyleTransformationEngine()

        result, plan = engine.apply_style_guide(report, guide, dry_run=False)

        for part in result.parts:
            if part.path.endswith("/visual.json") and isinstance(part.payload, dict):
                objs = part.payload.get("visual", {}).get("objects", {})
                for key, val in objs.items():
                    assert isinstance(val, list), f"objects.{key} should be a list, got {type(val)}"


class TestDimensionSnap:
    """Verify dimension snapping is applied and persisted to parts."""

    def test_positions_snapped_to_grid(self):
        report = _make_report([
            {"name": "v1", "type": "card", "x": 21, "y": 23, "w": 301, "h": 199},
        ])
        guide = _enterprise_guide()  # dimensionSnap=4
        engine = StyleTransformationEngine()

        result, plan = engine.apply_style_guide(report, guide, dry_run=False)

        for part in result.parts:
            if part.path.endswith("/visual.json") and isinstance(part.payload, dict):
                pos = part.payload["position"]
                assert pos["x"] == 20, f"x should snap 21→20, got {pos['x']}"
                assert pos["y"] == 24, f"y should snap 23→24, got {pos['y']}"
                assert pos["width"] == 300, f"width should snap 301→300"  # 301/4=75.25 → 300
                assert pos["height"] == 200, f"height should snap 199→200"


class TestSyncByPath:
    """Verify the sync step matches visuals by path, not just name."""

    def test_sync_matches_by_path(self):
        report = _make_report([
            {"name": "v1", "type": "card", "x": 10, "y": 10, "w": 200, "h": 100},
            {"name": "v1", "type": "multiRowCard", "x": 300, "y": 10, "w": 200, "h": 100},
        ])
        # Make second visual have a different path
        report.parts[1].path = "definition/pages/p1/visuals/v1_dup/visual.json"
        report.pages[0].visuals[1].id = "v1_dup"

        guide = _enterprise_guide()
        engine = StyleTransformationEngine()

        result, plan = engine.apply_style_guide(report, guide, dry_run=False)

        # Both parts should have been updated
        updated_count = sum(
            1 for p in result.parts
            if p.path.endswith("/visual.json") and isinstance(p.payload, dict)
            and p.payload.get("visual", {}).get("visualContainerObjects")
        )
        assert updated_count == 2, f"Expected 2 visuals with VCO, got {updated_count}"
