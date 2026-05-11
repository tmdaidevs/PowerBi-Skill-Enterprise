from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.models.schemas import (
    ReportDefinition,
    Severity,
    StyleGuide,
    TransformationChange,
    TransformationPlan,
    VisualDefinition,
    VisualElementStyle,
    VisualTypeRules,
    WarningItem,
)


# ---------------------------------------------------------------------------
# Font weight mapping
# ---------------------------------------------------------------------------

FONT_WEIGHT_MAP: dict[str, int] = {
    "thin": 100,
    "extralight": 200,
    "light": 300,
    "regular": 400,
    "medium": 500,
    "semibold": 600,
    "bold": 700,
    "extrabold": 800,
    "black": 900,
}


def _resolve_font_weight(weight: str) -> int:
    """Convert a weight name ('Bold', 'Regular') to a numeric value."""
    return FONT_WEIGHT_MAP.get(weight.lower(), 400)


# ---------------------------------------------------------------------------
# PBIR property path mapping for visual elements
# ---------------------------------------------------------------------------

# Maps typography element keys to the PBIR objects paths they control
TYPOGRAPHY_ELEMENT_MAP: dict[str, list[dict[str, str]]] = {
    "pageTitle": [
        {"object": "title", "fontSize": "fontSize", "fontWeight": "fontWeight", "fontColor": "fontColor"},
    ],
    "subtitle": [
        {"object": "subTitle", "fontSize": "fontSize", "fontWeight": "fontWeight", "fontColor": "fontColor"},
    ],
    "visualTitle": [
        {"object": "title", "fontSize": "fontSize", "fontWeight": "fontWeight", "fontColor": "fontColor"},
    ],
    "filterBarTitle": [
        {"object": "filterCard", "fontSize": "headerFontSize", "fontWeight": "headerFontWeight"},
    ],
    "axisLabels": [
        {"object": "categoryAxis", "fontSize": "labelFontSize", "fontWeight": "labelFontWeight", "fontColor": "labelFontColor"},
        {"object": "valueAxis", "fontSize": "labelFontSize", "fontWeight": "labelFontWeight", "fontColor": "labelFontColor"},
    ],
    "filterValues": [
        {"object": "filterCard", "fontSize": "fontSize", "fontWeight": "fontWeight"},
    ],
    "tableHeaders": [
        {"object": "columnHeaders", "fontSize": "fontSize", "fontWeight": "fontWeight", "fontColor": "fontColor"},
    ],
    "tableTotals": [
        {"object": "total", "fontSize": "fontSize", "fontWeight": "fontWeight", "fontColor": "fontColor"},
    ],
    "kpiValues": [
        {"object": "labels", "fontSize": "fontSize", "fontWeight": "fontWeight", "fontColor": "fontColor"},
    ],
}

# Maps visual type names to the PBIR visual type identifiers they match
VISUAL_TYPE_ALIASES: dict[str, list[str]] = {
    "table": ["tableEx", "table"],
    "matrix": ["pivotTable"],
    "lineChart": ["lineChart"],
    "stackedChart": ["stackedBarChart", "stackedColumnChart", "clusteredBarChart", "clusteredColumnChart"],
    "comboChart": ["lineClusteredColumnComboChart", "lineStackedColumnComboChart"],
    "barChart": ["barChart", "columnChart", "clusteredBarChart", "clusteredColumnChart"],
    "kpiCard": ["card", "multiRowCard"],
    "gauge": ["gauge"],
    "areaChart": ["areaChart", "stackedAreaChart"],
    "decompositionTree": ["decompositionTreeVisual"],
    "waterfall": ["waterfallChart"],
    "donutChart": ["donutChart", "pieChart"],
    "slicer": ["slicer"],
    "scatterChart": ["scatterChart"],
    "treemap": ["treemap"],
    "funnel": ["funnel"],
    "map": ["map", "filledMap", "shapeMap"],
    "ribbon": ["ribbonChart"],
}

# Maps VisualTypeRules fields to PBIR objects.* property paths
ELEMENT_TO_PBIR_MAP: dict[str, dict[str, str]] = {
    "header": {
        "object": "columnHeaders",
        "bgColor": "backColor",
        "fontSize": "fontSize",
        "fontWeight": "fontWeight",
        "fontColor": "fontColor",
    },
    "values": {
        "object": "values",
        "bgColor": "backColor",
        "fontSize": "fontSize",
        "fontWeight": "fontWeight",
        "fontColor": "fontColor",
    },
    "total": {
        "object": "total",
        "bgColor": "backColor",
        "fontSize": "fontSize",
        "fontWeight": "fontWeight",
        "fontColor": "fontColor",
    },
    "xAxis": {
        "object": "categoryAxis",
        "fontSize": "labelFontSize",
        "fontWeight": "labelFontWeight",
        "fontColor": "labelFontColor",
    },
    "yAxis": {
        "object": "valueAxis",
        "fontSize": "labelFontSize",
        "fontWeight": "labelFontWeight",
        "fontColor": "labelFontColor",
    },
    "legend": {
        "object": "legend",
        "fontSize": "fontSize",
        "fontWeight": "fontWeight",
        "fontColor": "labelColor",
        "position": "position",
    },
    "labels": {
        "object": "labels",
        "fontSize": "fontSize",
        "fontWeight": "fontWeight",
        "fontColor": "color",
    },
    "items": {
        "object": "items",
        "fontSize": "fontSize",
        "fontWeight": "fontWeight",
        "fontColor": "fontColor",
        "bgColor": "background",
    },
    "slicerHeader": {
        "object": "header",
        "fontSize": "fontSize",
        "fontWeight": "fontWeight",
        "fontColor": "fontColor",
        "bgColor": "background",
    },
}


class StyleTransformationEngine:
    EDITABLE_STYLE_FIELDS = {
        "backgroundColor",
        "textColor",
        "cornerRadius",
        "titleAlignment",
        "showBorder",
        "alternatingRows",
        "legendPosition",
        "dataLabelColor",
        # Extended fields
        "fontSize",
        "fontWeight",
        "fontColor",
        "fontFamily",
        "backColor",
        "labelFontSize",
        "labelFontWeight",
        "labelFontColor",
        "labelColor",
        "position",
        "headerFontSize",
        "headerFontWeight",
    }

    # Visual types that use category-based coloring
    CATEGORY_VISUAL_TYPES = {
        "donutChart", "pieChart", "treemap", "funnel",
        "waterfallChart", "sunburst",
        "barChart", "columnChart", "clusteredBarChart", "clusteredColumnChart",
        "stackedBarChart", "stackedColumnChart", "lineChart", "areaChart",
    }

    @staticmethod
    def extract_category_field(visual: VisualDefinition) -> dict[str, str] | None:
        """Extract the category field (entity + property) from a visual's query.

        Returns ``{"entity": ..., "property": ..., "queryRef": ...}`` if the
        visual has a Category projection, otherwise ``None``.
        """
        query_state = visual.raw.get("visual", {}).get("query", {}).get("queryState", {})
        category = query_state.get("Category", {})
        projections = category.get("projections", [])
        if not projections:
            return None

        field = projections[0].get("field", {})
        col = field.get("Column", {})
        entity = col.get("Expression", {}).get("SourceRef", {}).get("Entity")
        prop = col.get("Property")
        query_ref = projections[0].get("queryRef", "")
        if entity and prop:
            return {"entity": entity, "property": prop, "queryRef": query_ref}
        return None

    @staticmethod
    def build_category_data_points(
        entity: str,
        prop: str,
        category_values: list[str],
        palette: list[str],
    ) -> list[dict[str, Any]]:
        """Build per-category ``dataPoint`` entries with PBIR selectors."""
        data_points: list[dict[str, Any]] = []
        for idx, val in enumerate(category_values):
            color = palette[idx % len(palette)] if palette else "#888888"
            data_points.append({
                "properties": {
                    "fill": {
                        "solid": {
                            "color": {
                                "expr": {"Literal": {"Value": f"'{color}'"}}
                            }
                        }
                    }
                },
                "selector": {
                    "data": [
                        {
                            "scopeId": {
                                "Comparison": {
                                    "ComparisonKind": 0,
                                    "Left": {
                                        "Column": {
                                            "Expression": {"SourceRef": {"Entity": entity}},
                                            "Property": prop,
                                        }
                                    },
                                    "Right": {"Literal": {"Value": f"'{val}'"}},
                                }
                            }
                        }
                    ],
                },
            })
        return data_points

    def _apply_if_changed(self, plan: TransformationPlan, target: str, path: str, container: dict, key: str, new_value, risk_note: str | None = None) -> None:
        old_value = container.get(key)
        if old_value == new_value:
            return
        container[key] = new_value
        plan.changes.append(
            TransformationChange(target=target, path=path, old_value=old_value, new_value=new_value, risk_note=risk_note)
        )

    @staticmethod
    def _unwrap_pbir_object(visual_objects: dict, obj_key: str) -> dict:
        """Get a writable properties dict from a PBIR visual objects entry.

        PBIR objects can be either a dict or a list of dicts (e.g.
        ``[{"properties": {...}}]``). This normalizes to a flat dict
        suitable for ``_apply_if_changed``.
        """
        visual_objects.setdefault(obj_key, {})
        target = visual_objects[obj_key]
        if isinstance(target, list):
            if target and isinstance(target[0], dict):
                return target[0].setdefault("properties", {})
            props: dict = {}
            visual_objects[obj_key] = [{"properties": props}]
            return props
        return target

    def apply_style_guide(self, report: ReportDefinition, style_guide: StyleGuide, dry_run: bool = True) -> tuple[ReportDefinition, TransformationPlan]:
        mutable = deepcopy(report)
        plan = TransformationPlan(report_id=report.report_id, workspace_id=report.workspace_id, dry_run=dry_run)

        for page in mutable.pages:
            if len(page.visuals) > style_guide.rules.max_visuals_per_page:
                plan.warnings.append(
                    WarningItem(
                        severity=Severity.WARNING,
                        code="max_visuals_exceeded",
                        message=f"Page {page.name} has {len(page.visuals)} visuals; max is {style_guide.rules.max_visuals_per_page}",
                        remediation="Split page visuals or increase style guide threshold.",
                    )
                )

            page.properties.setdefault("canvas", {})
            self._apply_if_changed(
                plan,
                target=f"page:{page.id}",
                path="canvas.padding",
                container=page.properties["canvas"],
                key="padding",
                new_value=style_guide.layout.page_padding,
            )

            # Extended: apply page-level background from style guide
            if style_guide.colors and style_guide.colors.report_palette:
                primary_colors = style_guide.colors.report_palette.get("primary", [])
                # Find the page background color (usage contains "background")
                for color_entry in primary_colors:
                    if color_entry.usage and "background" in color_entry.usage.lower():
                        page.properties.setdefault("background", {})
                        self._apply_if_changed(
                            plan,
                            target=f"page:{page.id}",
                            path="background.color",
                            container=page.properties["background"],
                            key="color",
                            new_value=color_entry.hex,
                        )
                        break

            for visual in page.visuals:
                # Apply visual container objects (border radius, background, padding)
                # These go into the raw PBIR visual.json -> visualContainerObjects
                vco = visual.raw.setdefault("visualContainerObjects", {})

                def _lit(val: str) -> dict:
                    return {"expr": {"Literal": {"Value": val}}}

                def _color_expr(hex_val: str) -> dict:
                    return {"solid": {"color": {"expr": {"Literal": {"Value": f"'{hex_val}'"}}}}}

                # Corner radius via border
                if style_guide.layout.corner_radius is not None:
                    border_props = {}
                    border_props["show"] = _lit("true")
                    border_props["color"] = _color_expr("#E0E0E0")
                    border_props["radius"] = _lit(f"{style_guide.layout.corner_radius}D")
                    vco["border"] = [{"properties": border_props}]
                    plan.changes.append(TransformationChange(
                        target=f"visual:{visual.id}", path="visualContainerObjects.border.radius",
                        old_value=None, new_value=style_guide.layout.corner_radius))

                # Visual background color
                if style_guide.theme.background_color:
                    bg_props = {"color": _color_expr(style_guide.theme.background_color), "transparency": _lit("0D")}
                    vco["background"] = [{"properties": bg_props}]
                    plan.changes.append(TransformationChange(
                        target=f"visual:{visual.id}", path="visualContainerObjects.background.color",
                        old_value=None, new_value=style_guide.theme.background_color))

                # Inner padding (from layout.pagePadding or body.innerPadding)
                inner_pad = style_guide.layout.page_padding
                if style_guide.page_structure and style_guide.page_structure.body:
                    inner_pad = style_guide.page_structure.body.inner_padding or inner_pad
                if inner_pad and inner_pad > 0:
                    pad_props = {
                        "top": _lit(f"{inner_pad}D"),
                        "bottom": _lit(f"{inner_pad}D"),
                        "left": _lit(f"{inner_pad}D"),
                        "right": _lit(f"{inner_pad}D"),
                    }
                    vco["padding"] = [{"properties": pad_props}]

                # Also update the raw payload in report.parts so changes persist
                for part in mutable.parts if not dry_run else []:
                    if not part.path.endswith("/visual.json") or not isinstance(part.payload, dict):
                        continue
                    if part.payload.get("name") == (visual.name or visual.id):
                        part.payload.setdefault("visual", {})
                        part.payload["visual"]["visualContainerObjects"] = vco
                        break

                # Legacy: also set style dict for backward compat
                visual.properties.setdefault("style", {})
                style = visual.properties["style"]
                style["cornerRadius"] = style_guide.layout.corner_radius
                style["backgroundColor"] = style_guide.theme.background_color
                style["textColor"] = style_guide.theme.text_color

                type_rules = style_guide.visual_rules.get(visual.visual_type, {})
                for rule_key, rule_value in type_rules.items():
                    if rule_key not in self.EDITABLE_STYLE_FIELDS:
                        plan.warnings.append(
                            WarningItem(
                                severity=Severity.INFO,
                                code="non_editable_rule_skipped",
                                message=f"Skipped unsupported style rule '{rule_key}' for visual {visual.id}",
                                remediation="Add deterministic mapping before applying this rule.",
                            )
                        )
                        continue
                    self._apply_if_changed(
                        plan,
                        target=f"visual:{visual.id}",
                        path=f"style.{rule_key}",
                        container=style,
                        key=rule_key,
                        new_value=rule_value,
                    )

                if visual.visual_type.startswith("custom") and not style_guide.rules.allow_custom_visuals:
                    plan.warnings.append(
                        WarningItem(
                            severity=Severity.BLOCKER,
                            code="custom_visual_disallowed",
                            message=f"Custom visual {visual.id} violates style guide policy.",
                            remediation="Replace custom visual or set allowCustomVisuals=true.",
                        )
                    )

                # Extended: apply typography element rules
                self._apply_typography_to_visual(visual, style_guide, plan)

                # Extended: apply deep visual-type formatting rules
                # Check for page-level overrides first
                page_override_rules = None
                if style_guide.page_overrides and page.display_name in style_guide.page_overrides:
                    override = style_guide.page_overrides[page.display_name]
                    if override.visual_type_rules:
                        page_override_rules = override.visual_type_rules
                self._apply_visual_type_rules(visual, style_guide, plan, page_override_rules=page_override_rules)

                # Auto-snap dimensions to grid if dimensionSnap is set
                snap = style_guide.layout.dimension_snap
                if snap and snap > 0:
                    for dim_attr in ("x", "y", "width", "height"):
                        val = getattr(visual, dim_attr, None)
                        if val is not None:
                            snapped = round(val / snap) * snap
                            if snapped != val:
                                self._apply_if_changed(
                                    plan,
                                    target=f"visual:{visual.id}",
                                    path=f"position.{dim_attr}",
                                    container=visual.properties.setdefault("position", {}),
                                    key=dim_attr,
                                    new_value=snapped,
                                )
                                setattr(visual, dim_attr, snapped)

        if dry_run:
            return report, plan

        # Sync all visual model changes back to report.parts payloads
        # The engine modifies visual.objects, visual.raw, visual.x/y/w/h etc.
        # but parts still have the original payload — we must update them.
        for page in mutable.pages:
            for visual in page.visuals:
                for part in mutable.parts:
                    if not part.path.endswith("/visual.json") or not isinstance(part.payload, dict):
                        continue
                    if part.payload.get("name") != (visual.name or visual.id):
                        continue

                    # Sync position (dimension snap changes)
                    if visual.x is not None:
                        part.payload.setdefault("position", {})
                        part.payload["position"]["x"] = visual.x
                        part.payload["position"]["y"] = visual.y
                        part.payload["position"]["width"] = visual.width
                        part.payload["position"]["height"] = visual.height

                    # Sync objects (typography, visual type rules)
                    if visual.objects:
                        filtered_objects = {k: v for k, v in visual.objects.items() if not k.startswith("_")}
                        part.payload.setdefault("visual", {})["objects"] = filtered_objects

                    # Sync visualContainerObjects (border radius, background, padding)
                    vco = visual.raw.get("visualContainerObjects")
                    if vco:
                        part.payload.setdefault("visual", {})["visualContainerObjects"] = vco

                    break

        return mutable, plan

    # ------------------------------------------------------------------
    # Typography: per-element font application
    # ------------------------------------------------------------------

    def _apply_typography_to_visual(
        self,
        visual: VisualDefinition,
        style_guide: StyleGuide,
        plan: TransformationPlan,
    ) -> None:
        """Apply per-element typography rules (font family, size, weight) to a visual."""
        typo = style_guide.typography
        if not typo.elements and not typo.font_family and not typo.title_font_family:
            return

        visual.objects.setdefault("_typography_applied", {})
        font_family = style_guide.get_font_family()

        # Apply global font family to visual title if set
        if font_family:
            title_obj = self._unwrap_pbir_object(visual.objects, "title")
            self._apply_if_changed(
                plan,
                target=f"visual:{visual.id}",
                path="objects.title.fontFamily",
                container=title_obj,
                key="fontFamily",
                new_value=font_family,
            )

        if not typo.elements:
            # Legacy fallback: apply titleFontSize/bodyFontSize when elements not configured
            if typo.title_font_size:
                title_obj = self._unwrap_pbir_object(visual.objects, "title")
                self._apply_if_changed(plan, target=f"visual:{visual.id}",
                                       path="objects.title.fontSize", container=title_obj,
                                       key="fontSize", new_value=typo.title_font_size)
            if typo.body_font_size and visual.visual_type in ("card", "multiRowCard", "textbox"):
                labels_obj = self._unwrap_pbir_object(visual.objects, "labels")
                self._apply_if_changed(plan, target=f"visual:{visual.id}",
                                       path="objects.labels.fontSize", container=labels_obj,
                                       key="fontSize", new_value=typo.body_font_size)
            return

        # Determine which typography elements apply to this visual type
        for element_key, font_spec in typo.elements.items():
            mappings = TYPOGRAPHY_ELEMENT_MAP.get(element_key, [])
            for mapping in mappings:
                obj_key = mapping["object"]
                # Only apply relevant mappings to visuals that have the object
                if not self._visual_supports_object(visual.visual_type, obj_key):
                    continue

                target_obj = self._unwrap_pbir_object(visual.objects, obj_key)

                if "fontSize" in mapping:
                    self._apply_if_changed(
                        plan,
                        target=f"visual:{visual.id}",
                        path=f"objects.{obj_key}.{mapping['fontSize']}",
                        container=target_obj,
                        key=mapping["fontSize"],
                        new_value=font_spec.size,
                    )

                if "fontWeight" in mapping:
                    self._apply_if_changed(
                        plan,
                        target=f"visual:{visual.id}",
                        path=f"objects.{obj_key}.{mapping['fontWeight']}",
                        container=target_obj,
                        key=mapping["fontWeight"],
                        new_value=_resolve_font_weight(font_spec.weight),
                    )

                if font_spec.color and "fontColor" in mapping:
                    self._apply_if_changed(
                        plan,
                        target=f"visual:{visual.id}",
                        path=f"objects.{obj_key}.{mapping['fontColor']}",
                        container=target_obj,
                        key=mapping["fontColor"],
                        new_value=font_spec.color,
                    )

                if font_family:
                    self._apply_if_changed(
                        plan,
                        target=f"visual:{visual.id}",
                        path=f"objects.{obj_key}.fontFamily",
                        container=target_obj,
                        key="fontFamily",
                        new_value=font_family,
                    )

    @staticmethod
    def _visual_supports_object(visual_type: str, obj_key: str) -> bool:
        """Check whether a PBIR visual type supports a given objects key."""
        table_types = {"tableEx", "table", "pivotTable"}
        chart_types = {
            "lineChart", "barChart", "columnChart", "clusteredBarChart",
            "clusteredColumnChart", "stackedBarChart", "stackedColumnChart",
            "areaChart", "stackedAreaChart", "lineClusteredColumnComboChart",
            "lineStackedColumnComboChart", "waterfallChart", "donutChart", "pieChart",
        }
        card_types = {"card", "multiRowCard"}

        if obj_key in ("columnHeaders", "values", "total"):
            return visual_type in table_types
        if obj_key in ("categoryAxis", "valueAxis", "legend"):
            return visual_type in chart_types
        if obj_key == "labels":
            return visual_type in chart_types | card_types | {"gauge", "decompositionTreeVisual"}
        if obj_key in ("items", "header"):
            return visual_type == "slicer"
        if obj_key == "filterCard":
            return visual_type == "slicer"
        # title and subTitle apply to everything
        return obj_key in ("title", "subTitle")

    # ------------------------------------------------------------------
    # Deep visual-type formatting rules
    # ------------------------------------------------------------------

    def _resolve_visual_type_rules(
        self, visual: VisualDefinition, style_guide: StyleGuide,
        override_rules: dict[str, VisualTypeRules] | None = None,
    ) -> VisualTypeRules | None:
        """Find the matching VisualTypeRules for a visual, checking aliases."""
        rules_dict = override_rules or style_guide.visual_type_rules
        if not rules_dict:
            return None

        # Direct match by PBI visual type
        if visual.visual_type in rules_dict:
            return rules_dict[visual.visual_type]

        # Match via aliases
        for rule_name, rules in rules_dict.items():
            aliases = VISUAL_TYPE_ALIASES.get(rule_name, [])
            if visual.visual_type in aliases:
                return rules

        return None

    def _apply_visual_type_rules(
        self,
        visual: VisualDefinition,
        style_guide: StyleGuide,
        plan: TransformationPlan,
        page_override_rules: dict[str, VisualTypeRules] | None = None,
    ) -> None:
        """Apply deep per-visual-type formatting rules (header/values/total, axes, legend, etc.)."""
        # Page overrides take priority over global rules
        type_rules = None
        if page_override_rules:
            type_rules = self._resolve_visual_type_rules(visual, style_guide, override_rules=page_override_rules)
        if not type_rules:
            type_rules = self._resolve_visual_type_rules(visual, style_guide)
        if not type_rules:
            return

        # Resolve variant if applicable (e.g. table "v1" vs "v2")
        active_variant = type_rules.default_variant
        variant_elements: dict[str, VisualElementStyle] | None = None
        if type_rules.variants and active_variant and active_variant in type_rules.variants:
            variant_elements = {
                k: VisualElementStyle(**v) if isinstance(v, dict) else v
                for k, v in type_rules.variants[active_variant].items()
            }

        # Collect all element rules to apply
        elements_to_apply: dict[str, VisualElementStyle] = {}

        # Add top-level element rules
        for element_key in ("header", "values", "total", "x_axis", "y_axis", "legend", "labels"):
            attr_val = getattr(type_rules, element_key, None)
            if attr_val is not None:
                # Map Python attribute name back to JSON key
                json_key = element_key.replace("_a", "A").replace("_", "")  # x_axis → xAxis
                if element_key == "x_axis":
                    json_key = "xAxis"
                elif element_key == "y_axis":
                    json_key = "yAxis"
                elements_to_apply[json_key] = attr_val

        # Variant elements override top-level
        if variant_elements:
            elements_to_apply.update(variant_elements)

        # Apply each element's style to the visual's objects
        for element_key, element_style in elements_to_apply.items():
            mapping = ELEMENT_TO_PBIR_MAP.get(element_key)
            if not mapping:
                continue

            obj_key = mapping["object"]
            if not self._visual_supports_object(visual.visual_type, obj_key):
                continue

            visual.objects.setdefault(obj_key, {})
            target_obj = self._unwrap_pbir_object(visual.objects, obj_key)

            if element_style.font_size is not None and "fontSize" in mapping:
                self._apply_if_changed(
                    plan,
                    target=f"visual:{visual.id}",
                    path=f"objects.{obj_key}.{mapping['fontSize']}",
                    container=target_obj,
                    key=mapping["fontSize"],
                    new_value=element_style.font_size,
                )

            if element_style.font_weight is not None and "fontWeight" in mapping:
                self._apply_if_changed(
                    plan,
                    target=f"visual:{visual.id}",
                    path=f"objects.{obj_key}.{mapping['fontWeight']}",
                    container=target_obj,
                    key=mapping["fontWeight"],
                    new_value=_resolve_font_weight(element_style.font_weight),
                )

            if element_style.font_color is not None and "fontColor" in mapping:
                self._apply_if_changed(
                    plan,
                    target=f"visual:{visual.id}",
                    path=f"objects.{obj_key}.{mapping['fontColor']}",
                    container=target_obj,
                    key=mapping["fontColor"],
                    new_value=element_style.font_color,
                )

            if element_style.bg_color is not None and "bgColor" in mapping:
                bg_value = element_style.bg_color
                # For alternating rows, use the first color as the main bg
                if isinstance(bg_value, list):
                    bg_value = bg_value[0] if bg_value else None
                if bg_value:
                    self._apply_if_changed(
                        plan,
                        target=f"visual:{visual.id}",
                        path=f"objects.{obj_key}.{mapping['bgColor']}",
                        container=target_obj,
                        key=mapping["bgColor"],
                        new_value=bg_value,
                    )
                # Set alternating row colors if a list was provided
                if isinstance(element_style.bg_color, list) and len(element_style.bg_color) > 1:
                    target_obj["alternateBackColor"] = element_style.bg_color[1]

            if element_style.position is not None and "position" in mapping:
                self._apply_if_changed(
                    plan,
                    target=f"visual:{visual.id}",
                    path=f"objects.{obj_key}.{mapping['position']}",
                    container=target_obj,
                    key=mapping["position"],
                    new_value=element_style.position,
                )
