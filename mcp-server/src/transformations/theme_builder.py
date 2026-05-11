from __future__ import annotations

from typing import Any

from src.models.schemas import StyleGuide


class ThemeBuilder:
    """Builds a Power BI custom theme JSON from the extended style guide."""

    # Power BI theme advanced element color mapping:
    # style_guide field  →  PBI theme JSON key
    _ADVANCED_COLOR_MAP: dict[str, str] = {
        "first_level": "foregroundNeutralSecondary",
        "second_level": "foregroundNeutralTertiary",
        "third_level": "backgroundLight",
        "fourth_level": "backgroundNeutral",
        "background": "background",
        "secondary_background": "secondaryBackground",
    }

    @staticmethod
    def build(style_guide: StyleGuide, theme_name: str = "StyleGuideTheme") -> dict[str, Any]:
        """Build a complete PBI theme JSON dict.

        Args:
            style_guide: The extended style guide containing theme, color,
                and typography definitions.
            theme_name: Name embedded in the resulting theme JSON.

        Returns:
            A JSON-serializable dict conforming to the Power BI custom
            theme specification.
        """
        theme: dict[str, Any] = {
            "name": theme_name,
            "dataColors": style_guide.get_data_colors(),
            "foreground": style_guide.theme.text_color,
            "background": style_guide.theme.background_color,
            "tableAccent": style_guide.theme.primary_color,
        }

        # --- Extended color sections ---
        if style_guide.colors:
            colors = style_guide.colors

            if colors.sentiment:
                theme["sentimentColors"] = {
                    "good": colors.sentiment.positive,
                    "bad": colors.sentiment.negative,
                    "neutral": colors.sentiment.neutral,
                }

            if colors.divergent:
                theme["divergentColors"] = {
                    "minimum": colors.divergent.min,
                    "center": colors.divergent.middle,
                    "maximum": colors.divergent.max,
                }

            if colors.theme_advanced:
                adv = colors.theme_advanced
                for field, pbi_key in ThemeBuilder._ADVANCED_COLOR_MAP.items():
                    value = getattr(adv, field, None)
                    if value is not None:
                        theme[pbi_key] = value

        # --- Typography / textClasses ---
        font_family = style_guide.get_font_family()
        if font_family:
            font_entry = {"fontFamily": font_family}
            theme["textClasses"] = {
                "callout": font_entry,
                "title": font_entry.copy(),
                "header": font_entry.copy(),
                "label": font_entry.copy(),
            }

        return theme
