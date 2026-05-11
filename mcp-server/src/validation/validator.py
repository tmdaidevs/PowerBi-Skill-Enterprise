from __future__ import annotations

import re

from src.models.schemas import (
    ReportDefinition,
    ReportFormat,
    Severity,
    StyleGuide,
    ValidationResult,
    WarningItem,
)
from src.transformations.page_structure import PageStructureEngine


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    return int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)


def _relative_luminance(r: int, g: int, b: int) -> float:
    """Calculate relative luminance per WCAG 2.0."""
    def _linearize(c: int) -> float:
        s = c / 255.0
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    return 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b)


def _contrast_ratio(color1: str, color2: str) -> float:
    """Calculate WCAG contrast ratio between two hex colors."""
    l1 = _relative_luminance(*_hex_to_rgb(color1))
    l2 = _relative_luminance(*_hex_to_rgb(color2))
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


class ReportValidator:

    # ------------------------------------------------------------------
    # Core structural validation (existing)
    # ------------------------------------------------------------------

    def validate(self, report: ReportDefinition) -> ValidationResult:
        issues: list[WarningItem] = []

        if report.format != ReportFormat.PBIR:
            issues.append(
                WarningItem(
                    severity=Severity.BLOCKER,
                    code="unsupported_report_format",
                    message=f"Report format {report.format.value} is not safely editable for deterministic modernization.",
                    remediation="Convert to PBIR-compatible format before applying write operations.",
                )
            )

        if not report.parts:
            issues.append(
                WarningItem(
                    severity=Severity.BLOCKER,
                    code="missing_definition_parts",
                    message="No definition parts were returned by API.",
                    remediation="Re-export report definition and verify API permissions.",
                )
            )

        if not report.pages:
            issues.append(
                WarningItem(
                    severity=Severity.BLOCKER,
                    code="missing_pages",
                    message="No editable page definitions were found.",
                    remediation="Ensure report is PBIR and includes page artifacts.",
                )
            )

        page_ids = {p.id for p in report.pages}
        seen_visual_ids: set[str] = set()

        for page in report.pages:
            if page.id in (None, ""):
                issues.append(
                    WarningItem(
                        severity=Severity.BLOCKER,
                        code="missing_page_reference",
                        message="Page has missing ID",
                        remediation="Repair page metadata in source definition.",
                    )
                )

            for visual in page.visuals:
                if visual.page_id not in page_ids:
                    issues.append(
                        WarningItem(
                            severity=Severity.BLOCKER,
                            code="orphaned_visual_reference",
                            message=f"Visual {visual.id} references non-existent page {visual.page_id}",
                            remediation="Update visual->page mapping in definition.",
                        )
                    )
                if visual.id in seen_visual_ids:
                    issues.append(
                        WarningItem(
                            severity=Severity.WARNING,
                            code="duplicate_visual_id",
                            message=f"Duplicate visual id {visual.id}",
                            remediation="Ensure visual IDs are unique for reliable patching.",
                        )
                    )
                seen_visual_ids.add(visual.id)

                if isinstance(visual.properties, dict) and "parseError" in visual.properties:
                    issues.append(
                        WarningItem(
                            severity=Severity.BLOCKER,
                            code="malformed_visual_config",
                            message=f"Visual {visual.id} contains non-JSON config payload",
                            remediation="Normalize visual config JSON before applying patches.",
                        )
                    )

        # Validate visual positions don't overlap within each page
        for page in report.pages:
            positioned = [(v, v.x, v.y, v.width, v.height) for v in page.visuals
                         if v.x is not None and v.y is not None and v.width is not None and v.height is not None]
            for i, (va, ax, ay, aw, ah) in enumerate(positioned):
                for vb, bx, by, bw, bh in positioned[i+1:]:
                    if ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by:
                        issues.append(
                            WarningItem(
                                severity=Severity.BLOCKER,
                                code="visual_overlap",
                                message=f"Visuals '{va.name or va.id}' and '{vb.name or vb.id}' overlap on page '{page.name}'",
                                remediation="Use rearrange_page_visuals to fix spacing. All visuals must have consistent gaps with no overlaps.",
                            )
                        )

        # Validate consistent spacing between adjacent visuals
        MIN_GAP = 16  # minimum gap in pixels between visuals
        for page in report.pages:
            positioned = [(v, v.x, v.y, v.width, v.height) for v in page.visuals
                         if v.x is not None and v.y is not None and v.width is not None and v.height is not None]
            for i, (va, ax, ay, aw, ah) in enumerate(positioned):
                for vb, bx, by, bw, bh in positioned[i+1:]:
                    # Check horizontal adjacency (same row, within 40px y)
                    if abs(ay - by) < 40:
                        h_gap = bx - (ax + aw) if bx > ax else ax - (bx + bw)
                        if 0 < h_gap < MIN_GAP:
                            issues.append(
                                WarningItem(
                                    severity=Severity.WARNING,
                                    code="insufficient_visual_spacing",
                                    message=f"Visuals '{va.name or va.id}' and '{vb.name or vb.id}' have only {h_gap:.0f}px horizontal gap (min {MIN_GAP}px) on page '{page.name}'",
                                    remediation="Use rearrange_page_visuals with gap=20 to enforce consistent spacing.",
                                )
                            )

        for artifact in report.unsupported_artifacts:
            sev = Severity.BLOCKER if artifact == "missing_pages" else Severity.WARNING
            issues.append(
                WarningItem(
                    severity=sev,
                    code="unsupported_artifact",
                    message=f"Unsupported artifact detected: {artifact}",
                    remediation="Treat this artifact as read-only or remove before modernization.",
                )
            )

        valid = not any(i.severity == Severity.BLOCKER for i in issues)
        return ValidationResult(valid=valid, issues=issues)

    # ------------------------------------------------------------------
    # Extended: style-guide compliance validation
    # ------------------------------------------------------------------

    def validate_style_compliance(
        self,
        report: ReportDefinition,
        style_guide: StyleGuide,
    ) -> ValidationResult:
        """Validate a report against a style guide's extended rules.

        Checks font compliance, color palette compliance, dimension snapping,
        zone boundaries, and title consistency.
        """
        issues: list[WarningItem] = []

        # Run core validation first
        core_result = self.validate(report)
        issues.extend(core_result.issues)

        # Font compliance
        issues.extend(self._check_font_compliance(report, style_guide))

        # Color compliance
        issues.extend(self._check_color_compliance(report, style_guide))

        # Dimension snapping
        issues.extend(self._check_dimension_snapping(report, style_guide))

        # Zone boundary compliance
        issues.extend(self._check_zone_compliance(report, style_guide))

        # Title consistency
        issues.extend(self._check_title_consistency(report, style_guide))

        # Accessibility
        issues.extend(self._check_accessibility(report, style_guide))

        valid = not any(i.severity == Severity.BLOCKER for i in issues)
        return ValidationResult(valid=valid, issues=issues)

    # ------------------------------------------------------------------
    # Font compliance
    # ------------------------------------------------------------------

    @staticmethod
    def _check_font_compliance(
        report: ReportDefinition,
        style_guide: StyleGuide,
    ) -> list[WarningItem]:
        """Check that all visuals use an approved font family."""
        issues: list[WarningItem] = []
        approved = style_guide.rules.approved_fonts
        if not approved:
            # Also check typography.fontFamily as the single approved font
            font_family = style_guide.typography.font_family
            if font_family:
                approved = [font_family]
            else:
                return issues

        approved_lower = {f.lower() for f in approved}

        for page in report.pages:
            for visual in page.visuals:
                for obj_key, obj_val in visual.objects.items():
                    if isinstance(obj_val, dict):
                        font = obj_val.get("fontFamily")
                        if font and font.lower() not in approved_lower:
                            issues.append(
                                WarningItem(
                                    severity=Severity.WARNING,
                                    code="unapproved_font",
                                    message=f"Visual '{visual.name or visual.id}' uses unapproved font '{font}' in objects.{obj_key}",
                                    remediation=f"Change font to one of: {', '.join(approved)}",
                                )
                            )
        return issues

    # ------------------------------------------------------------------
    # Color palette compliance
    # ------------------------------------------------------------------

    @staticmethod
    def _check_color_compliance(
        report: ReportDefinition,
        style_guide: StyleGuide,
    ) -> list[WarningItem]:
        """Check that explicit fill colors are in the approved palette."""
        issues: list[WarningItem] = []

        # Build the set of all approved colors
        approved: set[str] = set()
        approved.update(c.upper() for c in style_guide.get_data_colors())
        approved.add(style_guide.theme.primary_color.upper())
        approved.add(style_guide.theme.background_color.upper())
        approved.add(style_guide.theme.text_color.upper())

        if style_guide.colors:
            if style_guide.colors.sentiment:
                approved.add(style_guide.colors.sentiment.positive.upper())
                approved.add(style_guide.colors.sentiment.negative.upper())
                approved.add(style_guide.colors.sentiment.neutral.upper())
            if style_guide.colors.divergent:
                approved.add(style_guide.colors.divergent.max.upper())
                approved.add(style_guide.colors.divergent.middle.upper())
                approved.add(style_guide.colors.divergent.min.upper())
            if style_guide.colors.report_palette:
                for tier_colors in style_guide.colors.report_palette.values():
                    approved.update(c.hex.upper() for c in tier_colors)
            for color in style_guide.get_category_colors().values():
                approved.add(color.upper())

        if not approved:
            return issues

        for page in report.pages:
            for visual in page.visuals:
                for obj_key, obj_val in visual.objects.items():
                    if isinstance(obj_val, dict):
                        for prop_key, prop_val in obj_val.items():
                            if isinstance(prop_val, str) and prop_val.startswith("#") and len(prop_val) in (4, 7, 9):
                                if prop_val.upper() not in approved:
                                    issues.append(
                                        WarningItem(
                                            severity=Severity.INFO,
                                            code="unapproved_color",
                                            message=f"Visual '{visual.name or visual.id}' uses color {prop_val} in objects.{obj_key}.{prop_key} which is not in the approved palette",
                                            remediation="Replace with an approved palette color.",
                                        )
                                    )
        return issues

    # ------------------------------------------------------------------
    # Dimension snapping
    # ------------------------------------------------------------------

    @staticmethod
    def _check_dimension_snapping(
        report: ReportDefinition,
        style_guide: StyleGuide,
    ) -> list[WarningItem]:
        """Check that visual x/y/width/height are multiples of the snap value."""
        issues: list[WarningItem] = []
        snap = style_guide.get_dimension_snap()
        if not snap:
            return issues

        for page in report.pages:
            for visual in page.visuals:
                for dim_name, dim_val in [("x", visual.x), ("y", visual.y), ("width", visual.width), ("height", visual.height)]:
                    if dim_val is not None and round(dim_val) % snap != 0:
                        issues.append(
                            WarningItem(
                                severity=Severity.WARNING,
                                code="dimension_not_snapped",
                                message=f"Visual '{visual.name or visual.id}' has {dim_name}={dim_val} which is not a multiple of {snap}",
                                remediation=f"Adjust {dim_name} to nearest multiple of {snap}: {round(dim_val / snap) * snap}",
                            )
                        )
        return issues

    # ------------------------------------------------------------------
    # Zone boundary compliance
    # ------------------------------------------------------------------

    @staticmethod
    def _check_zone_compliance(
        report: ReportDefinition,
        style_guide: StyleGuide,
    ) -> list[WarningItem]:
        """Check that visuals are within their designated body zone."""
        issues: list[WarningItem] = []
        if not style_guide.page_structure:
            return issues

        engine = PageStructureEngine()
        bounds = engine.compute_body_bounds(style_guide.page_structure)
        bx, by, bw, bh = bounds["x"], bounds["y"], bounds["width"], bounds["height"]

        for page in report.pages:
            for visual in page.visuals:
                if visual.x is None or visual.y is None:
                    continue
                vx, vy = visual.x, visual.y
                vw = visual.width or 0
                vh = visual.height or 0

                if vx < bx or vy < by or vx + vw > bx + bw or vy + vh > by + bh:
                    issues.append(
                        WarningItem(
                            severity=Severity.WARNING,
                            code="visual_outside_body_zone",
                            message=f"Visual '{visual.name or visual.id}' on page '{page.name}' extends outside the body zone ({bx},{by},{bw},{bh})",
                            remediation="Reposition the visual within the body zone boundaries.",
                        )
                    )
        return issues

    # ------------------------------------------------------------------
    # Title consistency
    # ------------------------------------------------------------------

    @staticmethod
    def _check_title_consistency(
        report: ReportDefinition,
        style_guide: StyleGuide,
    ) -> list[WarningItem]:
        """Check visual titles match the naming pattern if one is set."""
        issues: list[WarningItem] = []
        pattern = style_guide.rules.title_pattern
        if not pattern:
            return issues

        try:
            regex = re.compile(pattern)
        except re.error:
            return issues

        for page in report.pages:
            for visual in page.visuals:
                if visual.name and not regex.match(visual.name):
                    issues.append(
                        WarningItem(
                            severity=Severity.INFO,
                            code="title_pattern_mismatch",
                            message=f"Visual '{visual.name}' on page '{page.name}' does not match title pattern '{pattern}'",
                            remediation="Rename visual to match the naming convention.",
                        )
                    )
        return issues

    # ------------------------------------------------------------------
    # Accessibility (WCAG AA contrast)
    # ------------------------------------------------------------------

    @staticmethod
    def _check_accessibility(
        report: ReportDefinition,
        style_guide: StyleGuide,
    ) -> list[WarningItem]:
        """Check WCAG AA contrast ratios for text against backgrounds."""
        issues: list[WarningItem] = []

        # Check style guide's own color combinations
        bg_color = style_guide.theme.background_color
        text_color = style_guide.theme.text_color

        # Check global text vs background
        try:
            ratio = _contrast_ratio(text_color, bg_color)
            if ratio < 4.5:
                issues.append(WarningItem(
                    severity=Severity.WARNING,
                    code="low_contrast_ratio",
                    message=f"Text color {text_color} on background {bg_color} has contrast ratio {ratio:.1f}:1 (WCAG AA requires 4.5:1)",
                    remediation="Increase contrast between text and background colors.",
                ))
        except (ValueError, IndexError):
            pass

        # Check per-visual object colors
        for page in report.pages:
            for visual in page.visuals:
                objects = visual.objects if isinstance(visual.objects, dict) else {}
                for obj_key, obj_val in objects.items():
                    if not isinstance(obj_val, dict):
                        continue
                    font_color = obj_val.get("fontColor") or obj_val.get("labelFontColor") or obj_val.get("labelColor")
                    back_color = obj_val.get("backColor") or obj_val.get("background")
                    if not font_color or not back_color:
                        continue
                    if not (isinstance(font_color, str) and font_color.startswith("#")):
                        continue
                    if not (isinstance(back_color, str) and back_color.startswith("#")):
                        continue
                    try:
                        ratio = _contrast_ratio(font_color, back_color)
                        # Use 3:1 for large text (>=18pt), 4.5:1 for normal
                        font_size = obj_val.get("fontSize") or obj_val.get("labelFontSize") or 10
                        min_ratio = 3.0 if font_size >= 18 else 4.5
                        if ratio < min_ratio:
                            issues.append(WarningItem(
                                severity=Severity.WARNING,
                                code="low_contrast_ratio",
                                message=f"Visual '{visual.name or visual.id}' objects.{obj_key}: {font_color} on {back_color} has contrast ratio {ratio:.1f}:1 (min {min_ratio}:1 for {font_size}pt text)",
                                remediation="Increase contrast between text and background colors.",
                            ))
                    except (ValueError, IndexError):
                        pass

        # Check visualTypeRules color combinations from the style guide
        if style_guide.visual_type_rules:
            for vtype, rules in style_guide.visual_type_rules.items():
                for element_name in ("header", "values", "total"):
                    element = getattr(rules, element_name, None)
                    if element and element.font_color and element.bg_color:
                        bg = element.bg_color if isinstance(element.bg_color, str) else (element.bg_color[0] if element.bg_color else None)
                        if bg:
                            try:
                                ratio = _contrast_ratio(element.font_color, bg)
                                font_size = element.font_size or 10
                                min_ratio = 3.0 if font_size >= 18 else 4.5
                                if ratio < min_ratio:
                                    issues.append(WarningItem(
                                        severity=Severity.WARNING,
                                        code="low_contrast_style_guide",
                                        message=f"Style guide {vtype}.{element_name}: {element.font_color} on {bg} has contrast ratio {ratio:.1f}:1 (min {min_ratio}:1)",
                                        remediation="Adjust style guide colors for accessibility compliance.",
                                    ))
                            except (ValueError, IndexError):
                                pass

        return issues
