"""Zone-based page layout engine.

Positions visuals and elements into Header / Footer / Filter / Body zones
based on a style guide's ``pageStructure`` configuration.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Callable

from src.models.schemas import (
    BodyZone,
    CanvasSize,
    FilterPanelZone,
    FooterZone,
    HeaderZone,
    PageDefinition,
    PageStructure,
    ReportDefinition,
    Severity,
    StyleGuide,
    TransformationChange,
    TransformationPlan,
    WarningItem,
)


class PageStructureEngine:
    """Applies zone-based page layout from a style guide's pageStructure config."""

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def compute_body_bounds(self, structure: PageStructure) -> dict[str, int]:
        """Calculate the usable body area bounds given header/footer/filter zones.

        Returns a dict with keys ``x``, ``y``, ``width``, ``height`` describing
        the rectangle available for report visuals after reserving space for the
        header, footer, filter panel, and body margins.
        """
        canvas = structure.canvas or CanvasSize()
        header = structure.header or HeaderZone(height=0)
        footer = structure.footer or FooterZone(height=0)
        filter_panel = structure.filter_panel or FilterPanelZone(width=0)
        body = structure.body or BodyZone()

        # Vertical bounds --------------------------------------------------
        top = header.height + body.top_margin
        bottom = canvas.height - footer.height - body.bottom_margin
        body_height = max(bottom - top, 0)

        # Horizontal bounds ------------------------------------------------
        if filter_panel.side == "left":
            x = filter_panel.width + body.left_margin
            body_width = canvas.width - filter_panel.width - body.left_margin - body.right_margin
        else:
            # "right" (default)
            x = body.left_margin
            body_width = canvas.width - filter_panel.width - body.left_margin - body.right_margin

        body_width = max(body_width, 0)

        return {"x": x, "y": top, "width": body_width, "height": body_height}

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def apply_page_structure(
        self,
        report: ReportDefinition,
        style_guide: StyleGuide,
        dry_run: bool = True,
        image_creator: Callable | None = None,
    ) -> tuple[ReportDefinition, TransformationPlan]:
        """Apply zone-based layout to all pages in the report.

        Parameters
        ----------
        report:
            The parsed report definition to transform.
        style_guide:
            A ``StyleGuide`` whose ``page_structure`` field drives the layout.
        dry_run:
            When *True* (default) the returned report is the **original**
            object – no mutations are made.  When *False* the report is
            deep-copied first and the copy is mutated.
        image_creator:
            Optional callback invoked when *dry_run* is *False* to create
            image visuals for header/footer zone elements.  Signature::

                image_creator(page_name, image_url, position, name)

        Returns
        -------
        tuple[ReportDefinition, TransformationPlan]
            The (possibly mutated) report and the transformation plan
            describing all intended changes and warnings.
        """
        structure = style_guide.page_structure or PageStructure()
        canvas = structure.canvas or CanvasSize()

        plan = TransformationPlan(
            report_id=report.report_id,
            workspace_id=report.workspace_id,
            dry_run=dry_run,
        )

        if not dry_run:
            report = deepcopy(report)

        body_bounds = self.compute_body_bounds(structure)

        for page in report.pages:
            # (a) Record canvas-size change ----------------------------------
            plan.changes.append(
                TransformationChange(
                    target=f"page:{page.name or page.id}",
                    path="canvas.size",
                    old_value=page.properties.get("width_height"),
                    new_value={"width": canvas.width, "height": canvas.height},
                    risk_note="Canvas dimensions will be set to style-guide values.",
                )
            )

            # (a2) Apply zone background colors to page parts ----------------
            if not dry_run:
                for part in report.parts:
                    if not part.path.endswith("/page.json") or not isinstance(part.payload, dict):
                        continue
                    if part.payload.get("name") != page.name:
                        continue
                    # Set canvas size
                    part.payload["width"] = canvas.width
                    part.payload["height"] = canvas.height
                    # Apply zone background colors via objects
                    objects = part.payload.setdefault("objects", {})
                    if structure.header and structure.header.background_color:
                        objects.setdefault("headerBackground", [{"properties": {}}])
                        bg_props = objects["headerBackground"][0].setdefault("properties", {})
                        bg_props["color"] = {"solid": {"color": {"expr": {"Literal": {"Value": f"'{structure.header.background_color}'"}}}}}
                        plan.changes.append(TransformationChange(
                            target=f"page:{page.name}", path="headerBackground.color",
                            old_value=None, new_value=structure.header.background_color))
                    if structure.footer and structure.footer.background_color:
                        objects.setdefault("footerBackground", [{"properties": {}}])
                        bg_props = objects["footerBackground"][0].setdefault("properties", {})
                        bg_props["color"] = {"solid": {"color": {"expr": {"Literal": {"Value": f"'{structure.footer.background_color}'"}}}}}
                        plan.changes.append(TransformationChange(
                            target=f"page:{page.name}", path="footerBackground.color",
                            old_value=None, new_value=structure.footer.background_color))
                    if structure.filter_panel and structure.filter_panel.background_color:
                        objects.setdefault("filterPanelBackground", [{"properties": {}}])
                        bg_props = objects["filterPanelBackground"][0].setdefault("properties", {})
                        bg_props["color"] = {"solid": {"color": {"expr": {"Literal": {"Value": f"'{structure.filter_panel.background_color}'"}}}}}
                        plan.changes.append(TransformationChange(
                            target=f"page:{page.name}", path="filterPanelBackground.color",
                            old_value=None, new_value=structure.filter_panel.background_color))
                    break

            # (b) Check each visual against body bounds ----------------------
            bx = body_bounds["x"]
            by = body_bounds["y"]
            bw = body_bounds["width"]
            bh = body_bounds["height"]

            for visual in page.visuals:
                vx = visual.x or 0
                vy = visual.y or 0
                vw = visual.width or 0
                vh = visual.height or 0

                if (
                    vx < bx
                    or vy < by
                    or vx + vw > bx + bw
                    or vy + vh > by + bh
                ):
                    plan.warnings.append(
                        WarningItem(
                            severity=Severity.WARNING,
                            code="visual_outside_body",
                            message=(
                                f"Visual '{visual.name or visual.id}' on page "
                                f"'{page.name or page.id}' is outside the "
                                f"body bounds ({bx}, {by}, {bw}, {bh})."
                            ),
                            remediation=(
                                "Move or resize the visual so it fits within "
                                "the body zone."
                            ),
                        )
                    )

            # (c) Reposition slicers to filter panel -----------------------
            self._reposition_slicers_to_filter_panel(
                page, structure, plan, dry_run,
            )

            # (d) Record planned image additions from header/footer ----------
            self._record_zone_images(
                plan, page, "header", structure.header,
            )
            self._record_zone_images(
                plan, page, "footer", structure.footer,
            )

            # (e) Create image visuals when not a dry run --------------------
            if not dry_run and image_creator:
                for zone_name, zone in [("header", structure.header), ("footer", structure.footer)]:
                    if zone is None or not zone.elements:
                        continue
                    for element_key, placement in zone.elements.items():
                        if placement.url:
                            image_creator(
                                page_name=page.name,
                                image_url=placement.url,
                                position={
                                    "x": placement.x,
                                    "y": placement.y,
                                    "width": placement.width,
                                    "height": placement.height,
                                },
                                name=placement.name or element_key,
                            )

            # (f) Navigation buttons in footer zone --------------------------
            self._create_navigation_buttons(
                plan, page, structure.footer, canvas,
                dry_run=dry_run, image_creator=image_creator,
            )

        return report, plan

    # ------------------------------------------------------------------
    # Slicer repositioning
    # ------------------------------------------------------------------

    def _reposition_slicers_to_filter_panel(
        self,
        page: PageDefinition,
        structure: PageStructure,
        plan: TransformationPlan,
        dry_run: bool,
    ) -> None:
        """Move slicer visuals into the filter panel zone, stacked vertically."""
        filter_panel = structure.filter_panel or FilterPanelZone(width=0)
        if filter_panel.width == 0:
            return

        canvas = structure.canvas or CanvasSize()
        header = structure.header or HeaderZone(height=0)

        # Determine the filter panel x position
        if filter_panel.side == "left":
            filter_panel_x = 0
        else:
            filter_panel_x = canvas.width - filter_panel.width

        slicers = [v for v in page.visuals if v.visual_type == "slicer"]
        if not slicers:
            return

        current_y = header.height + filter_panel.top_padding
        gap = 8

        for slicer in slicers:
            old_x = slicer.x or 0
            old_y = slicer.y or 0
            old_width = slicer.width or 0
            slicer_height = slicer.height or 0

            new_x = filter_panel_x
            new_y = current_y
            new_width = filter_panel.width

            plan.changes.append(
                TransformationChange(
                    target=f"visual:{slicer.name or slicer.id}",
                    path="position",
                    old_value={"x": old_x, "y": old_y, "width": old_width},
                    new_value={"x": new_x, "y": new_y, "width": new_width},
                    risk_note=(
                        f"Slicer '{slicer.name or slicer.id}' repositioned "
                        f"into the filter panel zone."
                    ),
                )
            )

            if not dry_run:
                slicer.x = new_x
                slicer.y = new_y
                slicer.width = new_width

            current_y += slicer_height + gap

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _record_zone_images(
        plan: TransformationPlan,
        page,
        zone_name: str,
        zone: HeaderZone | FooterZone | None,
    ) -> None:
        """Append ``TransformationChange`` entries for image elements in a zone."""
        if zone is None or not zone.elements:
            pass  # fall through to check navigation_items
        else:
            for element_key, placement in zone.elements.items():
                plan.changes.append(
                    TransformationChange(
                        target=f"page:{page.name or page.id}",
                        path=f"{zone_name}.elements.{element_key}",
                        old_value=None,
                        new_value={
                            "url": placement.url,
                            "x": placement.x,
                            "y": placement.y,
                            "width": placement.width,
                            "height": placement.height,
                            "name": placement.name,
                        },
                        risk_note=f"Image element '{element_key}' will be added to the {zone_name} zone.",
                    )
                )

        # Record planned navigation button additions for footer zones
        if (
            isinstance(zone, FooterZone)
            and zone.navigation_items
        ):
            for idx, label in enumerate(zone.navigation_items):
                plan.changes.append(
                    TransformationChange(
                        target=f"page:{page.name or page.id}",
                        path=f"{zone_name}.navigation_items[{idx}]",
                        old_value=None,
                        new_value={"label": label},
                        risk_note=f"Navigation button '{label}' will be added to the {zone_name} zone.",
                    )
                )

    def _create_navigation_buttons(
        self,
        plan: TransformationPlan,
        page,
        footer: FooterZone | None,
        canvas: CanvasSize,
        *,
        dry_run: bool = True,
        image_creator: Callable | None = None,
    ) -> None:
        """Create evenly-spaced text-box visuals for footer navigation items.

        When *dry_run* is *False* and *image_creator* is provided, a visual is
        created for each navigation label.  The buttons are laid out
        horizontally starting after the footer logo with a small offset.
        """
        if footer is None or not footer.navigation_items:
            return

        nav_items = footer.navigation_items

        # Determine the width consumed by the footer logo (if any)
        logo_width = 0
        if footer.elements:
            for placement in footer.elements.values():
                logo_width = max(logo_width, placement.x + placement.width)

        start_x = logo_width + 48  # offset past the logo
        available_width = canvas.width - start_x - 128
        button_width = max(int(available_width / len(nav_items)), 1)
        footer_y = canvas.height - footer.height

        for idx, label in enumerate(nav_items):
            btn_x = start_x + idx * button_width
            position = {
                "x": btn_x,
                "y": footer_y,
                "width": button_width,
                "height": footer.height,
            }
            btn_name = f"nav_btn_{idx}"

            plan.changes.append(
                TransformationChange(
                    target=f"page:{page.name or page.id}",
                    path=f"footer.nav_button.{btn_name}",
                    old_value=None,
                    new_value={"label": label, **position},
                    risk_note=f"Navigation button '{label}' will be created in the footer zone.",
                )
            )

            if not dry_run and image_creator:
                image_creator(
                    page_name=page.name,
                    image_url="",
                    position=position,
                    name=btn_name,
                )
