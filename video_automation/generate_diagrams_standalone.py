#!/usr/bin/env python3
"""
Standalone diagram generator — creates 12 FilterMate diagrams as HTML + PNG.
No QGIS or OBS required. Just Python + Playwright (optional for PNG).
"""
import os
import sys
import json

# Add parent to path
sys.path.insert(0, os.path.dirname(__file__))

from diagrams.mermaid_definitions import DIAGRAMS

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output", "diagrams")

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    width: 1920px;
    height: 1080px;
    background: linear-gradient(135deg, #0f0c29, #1a1a2e, #16213e);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    overflow: hidden;
}
.title-bar {
    position: absolute;
    top: 30px;
    left: 0;
    right: 0;
    text-align: center;
}
.title-bar h1 {
    color: #4CAF50;
    font-size: 36px;
    font-weight: 600;
    letter-spacing: 1px;
    text-shadow: 0 2px 10px rgba(76, 175, 80, 0.3);
}
.title-bar .subtitle {
    color: #8892b0;
    font-size: 18px;
    margin-top: 8px;
}
.brand {
    position: absolute;
    bottom: 25px;
    right: 40px;
    color: #4a5568;
    font-size: 14px;
    letter-spacing: 2px;
}
.brand span { color: #4CAF50; font-weight: bold; }
.diagram-container {
    max-width: 1700px;
    max-height: 850px;
    padding: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
}
.mermaid {
    font-size: 16px !important;
}
.mermaid .node rect,
.mermaid .node polygon,
.mermaid .node circle {
    stroke-width: 2px !important;
}
</style>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>
mermaid.initialize({
    startOnLoad: true,
    theme: 'dark',
    themeVariables: {
        primaryColor: '#1565C0',
        primaryTextColor: '#e0e0e0',
        primaryBorderColor: '#42A5F5',
        lineColor: '#90CAF9',
        secondaryColor: '#2E7D32',
        tertiaryColor: '#1a1a2e',
        background: '#1a1a2e',
        mainBkg: '#1E1E2E',
        nodeBorder: '#42A5F5',
        clusterBkg: '#16213e',
        clusterBorder: '#2196F3',
        titleColor: '#e0e0e0',
        edgeLabelBackground: '#1a1a2e',
        fontSize: '16px'
    },
    flowchart: { useMaxWidth: true, htmlLabels: true, curve: 'basis' },
    sequence: { useMaxWidth: true, actorMargin: 80, mirrorActors: false },
    fontFamily: 'Segoe UI'
});
</script>
</head>
<body>
<div class="title-bar">
    <h1>TITLE_PLACEHOLDER</h1>
    <div class="subtitle">FilterMate v4.6.1 — QGIS Plugin</div>
</div>
<div class="diagram-container">
    <pre class="mermaid">
MERMAID_PLACEHOLDER
    </pre>
</div>
<div class="brand"><span>Filter</span>Mate</div>
</body>
</html>"""


def generate_html(diagram_id: str, diagram_data: dict, output_dir: str) -> str:
    """Generate HTML file for a diagram."""
    html = HTML_TEMPLATE.replace("TITLE_PLACEHOLDER", diagram_data["title"])
    html = html.replace("MERMAID_PLACEHOLDER", diagram_data["mermaid"])
    
    os.makedirs(output_dir, exist_ok=True)
    html_path = os.path.join(output_dir, f"{diagram_id}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    return html_path


def render_to_png(html_path: str, png_path: str, width: int = 1920, height: int = 1080) -> bool:
    """Render HTML to PNG using Playwright."""
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(f"file:///{os.path.abspath(html_path).replace(os.sep, '/')}")
            page.wait_for_timeout(3000)  # Wait for Mermaid to render
            page.screenshot(path=png_path, full_page=False)
            browser.close()
        return True
    except ImportError:
        print("  [INFO] Playwright not installed — PNG rendering skipped.")
        print("         Install with: pip install playwright && python -m playwright install chromium")
        return False
    except Exception as e:
        print(f"  [WARNING] PNG rendering failed for {html_path}: {e}")
        return False


def main():
    print(f"\n{'='*50}")
    print(f"  FilterMate Diagram Generator")
    print(f"  {len(DIAGRAMS)} diagrams to generate")
    print(f"{'='*50}\n")
    
    html_dir = os.path.join(OUTPUT_DIR, "html")
    png_dir = os.path.join(OUTPUT_DIR, "png")
    
    html_paths = []
    png_count = 0
    
    for diagram_id, diagram_data in DIAGRAMS.items():
        print(f"  [{diagram_id}] {diagram_data['title']}")
        
        # Generate HTML
        html_path = generate_html(diagram_id, diagram_data, html_dir)
        html_paths.append(html_path)
        print(f"    ✓ HTML: {html_path}")
        
        # Try PNG
        png_path = os.path.join(png_dir, f"{diagram_id}.png")
        os.makedirs(png_dir, exist_ok=True)
        if render_to_png(html_path, png_path):
            png_count += 1
            print(f"    ✓ PNG: {png_path}")
    
    print(f"\n  Done: {len(html_paths)} HTML files")
    if png_count > 0:
        print(f"        {png_count} PNG files")
    else:
        print(f"        PNG rendering skipped (install Playwright for PNG)")
    print()


if __name__ == "__main__":
    main()
