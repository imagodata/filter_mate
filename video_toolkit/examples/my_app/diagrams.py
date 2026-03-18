"""
Mermaid Diagram Definitions — Example
========================================
Define your Mermaid diagrams here. Each entry in DIAGRAMS maps a
diagram_id to a title and Mermaid diagram code.

These are generated with:
    python run.py --diagrams

And can be shown during sequences with:
    seq.show_diagram(recorder, "architecture")

Mermaid syntax reference: https://mermaid.js.org/
"""

DIAGRAMS: dict[str, dict] = {

    "overview": {
        "title": "Application Overview",
        "mermaid": """
flowchart TD
    User["👤 User"]
    App["📝 My App"]
    Files["📁 Files"]
    Settings["⚙️ Settings"]

    User -->|opens| App
    App -->|reads/writes| Files
    App -->|reads| Settings
    User -->|configures| Settings

    style User fill:#1976D2,color:#fff
    style App fill:#4CAF50,color:#fff
    style Files fill:#FF9800,color:#fff
    style Settings fill:#9C27B0,color:#fff
""",
    },

    "workflow": {
        "title": "Basic Workflow",
        "mermaid": """
sequenceDiagram
    participant U as User
    participant A as Application
    participant F as File System

    U->>A: Launch app
    A->>F: Load settings
    F-->>A: Settings loaded

    U->>A: Open file
    A->>F: Read file
    F-->>A: File contents
    A->>U: Display content

    U->>A: Edit content
    U->>A: Save (Ctrl+S)
    A->>F: Write file
    F-->>A: Saved
    A->>U: Confirm save
""",
    },

    "features": {
        "title": "Key Features",
        "mermaid": """
mindmap
  root((My App))
    Editing
      Syntax highlighting
      Auto-complete
      Find & Replace
    File Management
      New / Open / Save
      Recent files
      Export formats
    Customization
      Themes
      Font size
      Key bindings
    Integration
      Plugins
      CLI support
      API
""",
    },

}
