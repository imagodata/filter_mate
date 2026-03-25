"""
Diagram Generator
=================
Converts Mermaid diagram definitions into styled HTML pages and optionally
renders them to PNG via Playwright (headless Chromium).

Usage:
    from toolkit.diagram_generator import DiagramGenerator
    gen = DiagramGenerator(config["diagrams"])
    html_path = gen.generate_diagram(mermaid_code, "output/diagrams/01.html", title="Architecture")
    png_path  = gen.render_to_png(html_path, "output/diagrams/01.png")
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Look for template.html in the toolkit's templates/ directory
_TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "diagram.html"


class DiagramGenerator:
    """
    Generates styled HTML files from Mermaid diagram code and renders to PNG.

    Parameters
    ----------
    config : dict
        The 'diagrams' section from config.yaml.
    """

    def __init__(self, config: dict) -> None:
        self.output_dir = Path(config.get("output_dir", "output/diagrams"))
        self.width: int = config.get("width", 1920)
        self.height: int = config.get("height", 1080)
        self.theme: str = config.get("theme", "dark")
        self.bg_color: str = config.get("background_color", "#1a1a2e")
        self.font_family: str = config.get("font_family", "Segoe UI")
        # Optional branding for the template
        self.app_name: str = config.get("app_name", "App Tutorial")
        self.app_version: str = config.get("app_version", "")
        self.accent_color: str = config.get("accent_color", "#4CAF50")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Core generation
    # ------------------------------------------------------------------

    def generate_diagram(
        self,
        mermaid_code: str,
        output_path: str | Path,
        title: str = "",
    ) -> Path:
        """
        Create a standalone HTML file containing the rendered Mermaid diagram.

        Parameters
        ----------
        mermaid_code : str
            The raw Mermaid diagram definition.
        output_path : str | Path
            Where to write the HTML file.
        title : str
            Title displayed at the top of the slide.

        Returns
        -------
        Path
            Path to the generated HTML file.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        html = self._build_html(mermaid_code, title)
        output_path.write_text(html, encoding="utf-8")
        logger.info("Generated diagram HTML: %s", output_path)
        return output_path

    def generate_all_diagrams(
        self,
        definitions: dict,
        output_dir: Optional[str | Path] = None,
    ) -> dict[str, Path]:
        """
        Batch-generate HTML files for all diagram definitions.

        Parameters
        ----------
        definitions : dict
            Mapping of diagram_id -> {"title": str, "mermaid": str}.
        output_dir : str | Path, optional
            Override for output directory.

        Returns
        -------
        dict
            Mapping of diagram_id -> Path to generated HTML file.
        """
        out_dir = Path(output_dir) if output_dir else self.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        results: dict[str, Path] = {}
        for diagram_id, info in definitions.items():
            title = info.get("title", diagram_id)
            mermaid = info.get("mermaid", "")
            html_path = out_dir / f"{diagram_id}.html"
            self.generate_diagram(mermaid, html_path, title=title)
            results[diagram_id] = html_path
        logger.info("Generated %d diagram HTML files in %s", len(results), out_dir)
        return results

    # ------------------------------------------------------------------
    # PNG rendering (requires Playwright)
    # ------------------------------------------------------------------

    def render_to_png(
        self,
        html_path: str | Path,
        png_path: str | Path,
        width: Optional[int] = None,
        height: Optional[int] = None,
        wait_ms: int = 2000,
    ) -> Path:
        """
        Render an HTML diagram file to PNG using Playwright (headless Chromium).

        Falls back gracefully if Playwright is not installed.

        Parameters
        ----------
        html_path : str | Path
            Path to the HTML file to render.
        png_path : str | Path
            Output PNG path.
        width, height : int, optional
            Viewport size (defaults to config values).
        wait_ms : int
            Milliseconds to wait for Mermaid to render before screenshotting.

        Returns
        -------
        Path
            Path to the PNG file.
        """
        html_path = Path(html_path).resolve()
        png_path = Path(png_path)
        png_path.parent.mkdir(parents=True, exist_ok=True)
        w = width or self.width
        h = height or self.height

        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except ImportError:
            logger.warning(
                "Playwright not installed. Skipping PNG render for %s. "
                "Install with: pip install playwright && playwright install chromium",
                html_path.name,
            )
            return png_path

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": w, "height": h})
                page.goto(html_path.as_uri(), wait_until="networkidle")
                page.wait_for_timeout(wait_ms)
                page.screenshot(path=str(png_path), full_page=False)
                browser.close()
            logger.info("Rendered PNG: %s", png_path)
        except Exception as exc:  # noqa: BLE001
            logger.error("Playwright rendering failed for %s: %s", html_path.name, exc)
            raise

        return png_path

    def render_all_to_png(
        self,
        html_paths: dict[str, Path],
        output_dir: Optional[str | Path] = None,
    ) -> dict[str, Path]:
        """
        Batch render all HTML diagrams to PNG.

        Returns
        -------
        dict
            Mapping of diagram_id -> Path to PNG.
        """
        out_dir = Path(output_dir) if output_dir else self.output_dir
        results: dict[str, Path] = {}
        for diagram_id, html_path in html_paths.items():
            png_path = out_dir / f"{diagram_id}.png"
            try:
                self.render_to_png(html_path, png_path)
                results[diagram_id] = png_path
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to render '%s': %s", diagram_id, exc)
        return results

    # ------------------------------------------------------------------
    # HTML builder
    # ------------------------------------------------------------------

    def _build_html(self, mermaid_code: str, title: str) -> str:
        """Build a complete styled HTML page for the diagram."""
        if _TEMPLATE_PATH.exists():
            template = _TEMPLATE_PATH.read_text(encoding="utf-8")
            return (
                template
                .replace("{{TITLE}}", title)
                .replace("{{MERMAID_CODE}}", mermaid_code)
                .replace("{{BG_COLOR}}", self.bg_color)
                .replace("{{FONT_FAMILY}}", self.font_family)
                .replace("{{THEME}}", self.theme)
                .replace("{{APP_NAME}}", self.app_name)
                .replace("{{APP_VERSION}}", self.app_version)
                .replace("{{ACCENT_COLOR}}", self.accent_color)
            )
        # Inline fallback template
        return _INLINE_TEMPLATE.format(
            title=title,
            mermaid_code=mermaid_code,
            bg_color=self.bg_color,
            font_family=self.font_family,
            theme=self.theme,
            app_name=self.app_name,
            app_version=self.app_version,
            accent_color=self.accent_color,
        )


# ---------------------------------------------------------------------------
# Inline fallback template (used when templates/diagram.html is absent)
# ---------------------------------------------------------------------------
_INLINE_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1920" />
<title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: linear-gradient(135deg, {bg_color} 0%, #16213e 60%, #0f3460 100%);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    font-family: '{font_family}', 'Segoe UI', sans-serif;
    color: #e0e0e0;
    overflow: hidden;
  }}
  .slide-container {{
    width: 1920px;
    height: 1080px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    position: relative;
    padding: 40px;
  }}
  .title-bar {{
    position: absolute;
    top: 0; left: 0; right: 0;
    background: rgba(76, 175, 80, 0.15);
    border-bottom: 2px solid {accent_color};
    padding: 16px 40px;
    display: flex;
    align-items: center;
    gap: 16px;
  }}
  .title-text {{
    font-size: 28px;
    font-weight: 600;
    color: #fff;
  }}
  .subtitle {{
    font-size: 16px;
    color: {accent_color};
    margin-left: auto;
    font-style: italic;
  }}
  .diagram-wrapper {{
    margin-top: 80px;
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 1;
    animation: fadeIn 0.8s ease-in;
  }}
  .footer {{
    position: absolute;
    bottom: 0; left: 0; right: 0;
    background: rgba(0,0,0,0.3);
    padding: 10px 40px;
    font-size: 13px;
    color: rgba(255,255,255,0.5);
    border-top: 1px solid rgba(76,175,80,0.2);
  }}
  @keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(20px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
  }}
</style>
</head>
<body>
<div class="slide-container">
  <div class="title-bar">
    <div class="title-text">{title}</div>
    <div class="subtitle">{app_name}{' ' + app_version if app_version else ''}</div>
  </div>
  <div class="diagram-wrapper">
    <div class="mermaid">
{mermaid_code}
    </div>
  </div>
  <div class="footer">{app_name}</div>
</div>
<script>
  mermaid.initialize({{
    startOnLoad: true,
    theme: '{theme}',
    themeVariables: {{
      primaryColor: '#1976D2',
      primaryTextColor: '#ffffff',
      primaryBorderColor: '{accent_color}',
      lineColor: '{accent_color}',
      secondaryColor: '#16213e',
      tertiaryColor: '#0f3460',
      background: '{bg_color}',
      mainBkg: '#16213e',
      nodeBorder: '{accent_color}',
      clusterBkg: 'rgba(76,175,80,0.1)',
      titleColor: '#ffffff',
      edgeLabelBackground: '#16213e',
      fontSize: '18px',
    }},
    flowchart: {{ curve: 'basis', padding: 20 }},
    sequence: {{ actorMargin: 80, mirrorActors: false }},
    fontFamily: '{font_family}, Segoe UI, sans-serif',
  }});
</script>
</body>
</html>
"""
