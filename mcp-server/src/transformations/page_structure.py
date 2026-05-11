"""Zone-based page layout engine.

Positions visuals and elements into Header / Footer / Filter / Body zones
based on a style guide's ``pageStructure`` configuration.
"""

from __future__ import annotations

from copy import deepcopy

from src.models.schemas import (
    BodyZone,
    CanvasSize,
    FilterPanelZone,
    FooterZone,
    HeaderZone,
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

            # (c) Record planned image additions from header/footer ----------
            self._record_zone_images(
                plan, page, "header", structure.header,
            )
            self._record_zone_images(
                plan, page, "footer", structure.footer,
            )

        return report, plan

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
            return

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
