#!/usr/bin/env python3
"""
Extract all diagrams (Mermaid + HTML tables + signal flow chains) from markdown files
and export each as a standalone HTML file.

Output: website/diagrams/  (one .html per diagram)
"""

import os
import re
import unicodedata

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_DIR = os.path.dirname(BASE_DIR)
OUTPUT_DIR = os.path.join(BASE_DIR, "diagrams")
ICONS_REL = "../icons"  # relative from website/ — diagrams/ is inside website/

os.makedirs(OUTPUT_DIR, exist_ok=True)


def slugify(text: str) -> str:
    """Convert a title to a filename-safe slug."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_]+", "-", text.strip())
    text = re.sub(r"-+", "-", text)
    return text[:80]


def wrap_mermaid_html(title: str, mermaid_code: str, source_file: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #1a1a2e;
      color: #e0e0e0;
      margin: 0;
      padding: 20px;
      display: flex;
      flex-direction: column;
      align-items: center;
      min-height: 100vh;
    }}
    h1 {{
      color: #4fc3f7;
      font-size: 1.3em;
      margin-bottom: 4px;
      text-align: center;
    }}
    .source {{
      color: #888;
      font-size: 0.75em;
      margin-bottom: 20px;
    }}
    .mermaid {{
      background: #fff;
      border-radius: 12px;
      padding: 24px;
      max-width: 95vw;
      overflow-x: auto;
    }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <div class="source">{source_file}</div>
  <div class="mermaid">
{mermaid_code}
  </div>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
  <script>
    mermaid.initialize({{
      startOnLoad: true,
      theme: 'default',
      securityLevel: 'loose',
      flowchart: {{ htmlLabels: true, curve: 'basis' }},
      sequence: {{ mirrorActors: false }}
    }});
  </script>
</body>
</html>"""


def wrap_html_table(title: str, table_html: str, source_file: str) -> str:
    # Fix icon paths: ../icons/ → ../../icons/ (diagrams/ is one level deeper)
    table_html = table_html.replace('src="../icons/', 'src="../../icons/')
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #1a1a2e;
      color: #e0e0e0;
      margin: 0;
      padding: 20px;
      display: flex;
      flex-direction: column;
      align-items: center;
      min-height: 100vh;
    }}
    h1 {{
      color: #4fc3f7;
      font-size: 1.3em;
      margin-bottom: 4px;
      text-align: center;
    }}
    .source {{
      color: #888;
      font-size: 0.75em;
      margin-bottom: 20px;
    }}
    .diagram-container {{
      background: #fff;
      border-radius: 12px;
      padding: 24px;
      max-width: 900px;
      width: 95vw;
      overflow-x: auto;
    }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <div class="source">{source_file}</div>
  <div class="diagram-container">
{table_html}
  </div>
</body>
</html>"""


def wrap_flow_chain(title: str, code_block: str, source_file: str) -> str:
    import html as html_mod
    escaped = html_mod.escape(code_block)
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #1a1a2e;
      color: #e0e0e0;
      margin: 0;
      padding: 20px;
      display: flex;
      flex-direction: column;
      align-items: center;
      min-height: 100vh;
    }}
    h1 {{
      color: #4fc3f7;
      font-size: 1.3em;
      margin-bottom: 4px;
      text-align: center;
    }}
    .source {{
      color: #888;
      font-size: 0.75em;
      margin-bottom: 20px;
    }}
    pre {{
      background: #0d1117;
      border: 1px solid #30363d;
      border-radius: 12px;
      padding: 24px;
      max-width: 900px;
      width: 90vw;
      overflow-x: auto;
      font-family: 'Fira Code', 'Cascadia Code', 'JetBrains Mono', monospace;
      font-size: 0.9em;
      line-height: 1.6;
      color: #c9d1d9;
    }}
    .arrow {{ color: #7ee787; }}
    .signal {{ color: #d2a8ff; }}
    .method {{ color: #79c0ff; }}
    .comment {{ color: #8b949e; font-style: italic; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <div class="source">{source_file}</div>
  <pre>{escaped}</pre>
</body>
</html>"""


def extract_mermaid_diagrams(filepath: str):
    """Extract all mermaid code blocks with their preceding title."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    diagrams = []
    i = 0
    diagram_counter = 0

    while i < len(lines):
        if lines[i].strip() == "```mermaid":
            # Find the title: look backwards for a heading
            title = None
            for j in range(i - 1, max(i - 8, -1), -1):
                if j >= 0 and re.match(r'^#{1,4}\s+', lines[j]):
                    title = re.sub(r'^#{1,4}\s+', '', lines[j]).strip()
                    # Clean emoji prefixes
                    title = re.sub(r'^[🗺️🎬📦🔍🧩🏗️⚙️🔧💡📊🛡️🧪📝🔌]+\s*', '', title)
                    break

            if not title:
                diagram_counter += 1
                title = f"Diagram {diagram_counter}"

            # Collect mermaid content
            mermaid_lines = []
            i += 1
            while i < len(lines) and lines[i].strip() != "```":
                mermaid_lines.append(lines[i])
                i += 1

            diagrams.append({
                "type": "mermaid",
                "title": title,
                "content": "\n".join(mermaid_lines),
            })
        i += 1

    return diagrams


def extract_html_table_diagrams(filepath: str):
    """Extract HTML table diagrams preceded by ### Diagramme or ### Visuel headings."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    diagrams = []
    i = 0

    while i < len(lines):
        # Look for heading that signals a diagram
        # Handles: ### Diagramme — Title, ### Diagramme 1 — Title, ## DIAGRAMME — Title, ### Visuel — Title
        heading_match = re.match(r'^#{2,4}\s+(Diagramme|Visuel|DIAGRAMME|VISUEL)\s*\d*\s*[—–-]\s*(.+)', lines[i], re.IGNORECASE)
        if heading_match:
            title = heading_match.group(2).strip()

            # Skip ahead to find <table
            j = i + 1
            while j < len(lines) and j < i + 15:
                if '<table' in lines[j].lower():
                    # Collect entire table
                    table_lines = []
                    depth = 0
                    while j < len(lines):
                        table_lines.append(lines[j])
                        depth += lines[j].lower().count('<table') - lines[j].lower().count('</table')
                        if depth <= 0 and '</table>' in lines[j].lower():
                            break
                        j += 1

                    diagrams.append({
                        "type": "html_table",
                        "title": title,
                        "content": "\n".join(table_lines),
                    })
                    break
                j += 1
        i += 1

    return diagrams


def extract_flow_chains(filepath: str):
    """Extract signal flow chains from knowledge base files (plain ``` code blocks with context title)."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    diagrams = []
    i = 0

    while i < len(lines):
        # Look for code blocks under headings like ### Chain N: ...
        if lines[i].strip() == "```" or (lines[i].strip().startswith("```") and lines[i].strip() != "```mermaid"):
            # Find title
            title = None
            for j in range(i - 1, max(i - 6, -1), -1):
                if j >= 0 and re.match(r'^#{2,4}\s+', lines[j]):
                    title = re.sub(r'^#{2,4}\s+', '', lines[j]).strip()
                    break

            if not title:
                i += 1
                continue

            # Only extract chains/flows that look like signal flows (contain arrows)
            code_lines = []
            i += 1
            while i < len(lines) and lines[i].strip() != "```":
                code_lines.append(lines[i])
                i += 1

            code_content = "\n".join(code_lines)
            # Only keep if it contains arrow patterns (signal flows)
            if "→" in code_content or "->" in code_content or ">>>" in code_content:
                diagrams.append({
                    "type": "flow_chain",
                    "title": title,
                    "content": code_content,
                })
        i += 1

    return diagrams


def main():
    # Files to scan
    website_dir = BASE_DIR
    knowledge_dir = os.path.join(PLUGIN_DIR, "knowledge")
    serena_dir = os.path.join(PLUGIN_DIR, ".serena")

    # Collect all markdown files
    scan_files = []

    # Website .md files
    for f in sorted(os.listdir(website_dir)):
        if f.endswith(".md"):
            scan_files.append(os.path.join(website_dir, f))

    # Knowledge .md files
    if os.path.isdir(knowledge_dir):
        for f in sorted(os.listdir(knowledge_dir)):
            if f.endswith(".md"):
                scan_files.append(os.path.join(knowledge_dir, f))

    # .serena .md files
    if os.path.isdir(serena_dir):
        for f in os.listdir(serena_dir):
            if f.endswith(".md"):
                scan_files.append(os.path.join(serena_dir, f))

    all_diagrams = []
    file_counters = {}

    for filepath in scan_files:
        rel = os.path.relpath(filepath, PLUGIN_DIR)
        basename = os.path.splitext(os.path.basename(filepath))[0]

        # Extract mermaid diagrams
        mermaid = extract_mermaid_diagrams(filepath)
        for d in mermaid:
            d["source_file"] = rel
            d["file_base"] = basename
            all_diagrams.append(d)

        # Extract HTML table diagrams
        tables = extract_html_table_diagrams(filepath)
        for d in tables:
            d["source_file"] = rel
            d["file_base"] = basename
            all_diagrams.append(d)

        # Extract flow chains (only from knowledge dir)
        if knowledge_dir in filepath:
            chains = extract_flow_chains(filepath)
            for d in chains:
                d["source_file"] = rel
                d["file_base"] = basename
                all_diagrams.append(d)

    # Write each diagram as standalone HTML
    written = 0
    for d in all_diagrams:
        file_base = d["file_base"].lower()
        title_slug = slugify(d["title"])

        # Track counter per file to ensure unique filenames
        key = f"{file_base}_{title_slug}"
        if key in file_counters:
            file_counters[key] += 1
            filename = f"{file_base}_{title_slug}_{file_counters[key]}.html"
        else:
            file_counters[key] = 1
            filename = f"{file_base}_{title_slug}.html"

        outpath = os.path.join(OUTPUT_DIR, filename)

        if d["type"] == "mermaid":
            html = wrap_mermaid_html(d["title"], d["content"], d["source_file"])
        elif d["type"] == "html_table":
            html = wrap_html_table(d["title"], d["content"], d["source_file"])
        elif d["type"] == "flow_chain":
            html = wrap_flow_chain(d["title"], d["content"], d["source_file"])
        else:
            continue

        with open(outpath, "w", encoding="utf-8") as f:
            f.write(html)

        d["filename"] = filename
        written += 1
        print(f"  [{d['type']:12s}] {filename}")

    # Generate index.html
    generate_index(all_diagrams)

    print(f"\n{'='*60}")
    print(f"Total: {written} diagrams exported to {os.path.relpath(OUTPUT_DIR, PLUGIN_DIR)}/")
    print(f"  - Mermaid:     {sum(1 for d in all_diagrams if d['type'] == 'mermaid')}")
    print(f"  - HTML tables: {sum(1 for d in all_diagrams if d['type'] == 'html_table')}")
    print(f"  - Flow chains: {sum(1 for d in all_diagrams if d['type'] == 'flow_chain')}")
    print(f"  + index.html generated")


def generate_index(diagrams):
    """Generate an index.html listing all diagrams grouped by source file."""
    # Group by source file
    groups = {}
    for d in diagrams:
        src = d["source_file"]
        if src not in groups:
            groups[src] = []
        groups[src].append(d)

    type_icons = {"mermaid": "&#x1F4CA;", "html_table": "&#x1F5BC;", "flow_chain": "&#x26A1;"}
    type_colors = {"mermaid": "#4fc3f7", "html_table": "#81c784", "flow_chain": "#ffb74d"}

    cards_html = ""
    total = len(diagrams)
    for source, items in groups.items():
        cards_html += f'<div class="group"><h2>{source} <span class="count">({len(items)})</span></h2>\n'
        for d in items:
            t = d["type"]
            icon = type_icons.get(t, "")
            color = type_colors.get(t, "#ccc")
            cards_html += f'  <a href="{d["filename"]}" class="card" style="border-left: 4px solid {color};">\n'
            cards_html += f'    <span class="icon">{icon}</span>\n'
            cards_html += f'    <span class="title">{d["title"]}</span>\n'
            cards_html += f'    <span class="badge" style="background:{color};">{t}</span>\n'
            cards_html += f'  </a>\n'
        cards_html += '</div>\n'

    index_html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>FilterMate — Diagrams Index ({total})</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #0f0f23;
      color: #e0e0e0;
      padding: 24px;
    }}
    h1 {{
      text-align: center;
      color: #4fc3f7;
      margin-bottom: 8px;
      font-size: 1.8em;
    }}
    .subtitle {{
      text-align: center;
      color: #888;
      margin-bottom: 32px;
      font-size: 0.9em;
    }}
    .legend {{
      display: flex;
      justify-content: center;
      gap: 24px;
      margin-bottom: 24px;
      flex-wrap: wrap;
    }}
    .legend span {{
      font-size: 0.85em;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .legend .dot {{
      width: 12px;
      height: 12px;
      border-radius: 50%;
      display: inline-block;
    }}
    .group {{
      margin-bottom: 32px;
    }}
    .group h2 {{
      color: #b0bec5;
      font-size: 1.05em;
      margin-bottom: 12px;
      padding-bottom: 6px;
      border-bottom: 1px solid #333;
    }}
    .group h2 .count {{
      color: #666;
      font-weight: normal;
    }}
    .card {{
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 16px;
      margin-bottom: 4px;
      background: #1a1a2e;
      border-radius: 6px;
      text-decoration: none;
      color: #e0e0e0;
      transition: background 0.15s;
    }}
    .card:hover {{
      background: #252545;
    }}
    .card .icon {{
      font-size: 1.2em;
      width: 28px;
      text-align: center;
    }}
    .card .title {{
      flex: 1;
    }}
    .card .badge {{
      font-size: 0.7em;
      padding: 2px 8px;
      border-radius: 10px;
      color: #000;
      font-weight: 600;
      text-transform: uppercase;
    }}
  </style>
</head>
<body>
  <h1>FilterMate — Diagrams</h1>
  <div class="subtitle">{total} diagrams extracted from documentation</div>
  <div class="legend">
    <span><span class="dot" style="background:#4fc3f7;"></span> Mermaid ({sum(1 for d in diagrams if d['type']=='mermaid')})</span>
    <span><span class="dot" style="background:#81c784;"></span> HTML Table ({sum(1 for d in diagrams if d['type']=='html_table')})</span>
    <span><span class="dot" style="background:#ffb74d;"></span> Flow Chain ({sum(1 for d in diagrams if d['type']=='flow_chain')})</span>
  </div>
{cards_html}
</body>
</html>"""

    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)


if __name__ == "__main__":
    main()
