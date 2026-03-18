# Examples — How to Create Your Own Video Project

This directory contains a complete example showing how to use **Video Toolkit**
for a hypothetical "Notepad" application tutorial. Adapt it for your own app.

---

## Directory Structure

```
my_app/
├── config.yaml        # App-specific configuration
├── automator.py       # Your AppAutomator subclass
├── diagrams.py        # Mermaid diagram definitions
├── sequences/
│   ├── __init__.py    # SEQUENCES list (ordered)
│   ├── intro.py       # First sequence (TimelineSequence)
│   └── demo.py        # Second sequence (VideoSequence)
└── run.py             # CLI entry point (orchestrator)
```

---

## Step-by-Step: Creating Your Own Project

### 1. Copy the example

```bash
cp -r examples/my_app my_project/
cd my_project/
```

### 2. Edit `config.yaml`

Change `window_title` to match your app's window title. All other values
can be tuned later.

```yaml
app:
  window_title: "My Application - Main Window"
```

### 3. Create your automator

Edit `automator.py` and add methods for every interaction your sequences need:

```python
from toolkit.app_automator import AppAutomator

class MyAutomator(AppAutomator):
    def click_main_button(self):
        self.click_region("main_button")
        self.wait(0.5)

    def enter_search_query(self, query: str):
        self.click_region("search_bar")
        self.clear_field()
        self.type_text_unicode(query)
        self.press_key("return")
        self.wait(1.0)
```

### 4. Calibrate UI positions

Run the interactive calibration tool to record UI element coordinates:

```bash
cd my_project/
python ../../scripts/calibrate.py --config config.yaml
```

Commands in the calibration menu:
- `all` — Full calibration session (go through all groups)
- `group <id>` — Calibrate a specific group
- `list` — Show current positions
- `review` — Visual review (cursor moves to each position)
- `live` — Real-time mouse position display

Customize the `GROUPS` dict in `calibrate.py` to match your app's UI.

### 5. Write your sequences

**Option A: VideoSequence** (simple, manual timing)

```python
from toolkit.sequence import VideoSequence

class MySequence(VideoSequence):
    name = "My Sequence"
    sequence_id = "seq00"
    duration_estimate = 20.0

    def execute(self, recorder, app, config):
        app.focus_window()
        app.click_region("main_button")
        app.wait(2.0)
        app.type_text_unicode("Hello!")
        app.wait(1.0)
```

**Option B: TimelineSequence** (narration-synchronized, precise timing)

```python
from toolkit.sequence import TimelineSequence
from toolkit.timeline import NarrationCue

class MySequence(TimelineSequence):
    name = "My Sequence"
    sequence_id = "seq00"

    def build_timeline(self, recorder, app, config):
        return [
            NarrationCue(
                text="Welcome to the application.",
                actions=lambda: app.focus_window(),
            ),
            NarrationCue(
                text="Let's click the main button.",
                actions=lambda: app.click_region("main_button"),
                post_delay=1.0,
            ),
        ]
```

### 6. Define your diagrams (optional)

Edit `diagrams.py` with Mermaid diagram code:

```python
DIAGRAMS = {
    "architecture": {
        "title": "System Architecture",
        "mermaid": """
flowchart TD
    UI["User Interface"] --> Core["Core Logic"]
    Core --> DB["Database"]
""",
    },
}
```

Generate them:
```bash
python run.py --diagrams
```

### 7. Register sequences

Edit `sequences/__init__.py`:

```python
from .intro import IntroSequence
from .demo import DemoSequence
from .advanced import AdvancedSequence

SEQUENCES = [IntroSequence, DemoSequence, AdvancedSequence]
```

### 8. Configure OBS (desktop mode)

```bash
python run.py --setup-obs
```

Or manually create scenes in OBS Studio:
- `App Fullscreen` — Display capture
- `Diagram Overlay` — Browser source (HTML files)
- `Intro` / `Outro` — Title cards

### 9. Test a single sequence

```bash
python run.py --sequence 0 --dry-run  # Preview
python run.py --sequence 0            # Execute
```

### 10. Run the full pipeline

```bash
# Desktop mode (OBS):
python run.py --all

# Headless mode (Docker/Xvfb):
python run.py --capture --all
```

---

## NarrationCue Sync Modes

| Mode       | Behavior                                          |
|------------|---------------------------------------------------|
| `"during"` | Actions + narration run in parallel (default)     |
| `"after"`  | Narration plays, then actions run                 |
| `"before"` | Actions run, then narration plays                 |

```python
NarrationCue(
    text="This dialog appears after the action.",
    actions=lambda: app.click_region("open_dialog"),
    sync="before",  # Click first, THEN narration plays
    post_delay=1.0,
)
```

---

## Two Recording Modes

### Desktop Mode (OBS Studio)
- **Best quality** — hardware-accelerated encoding
- Requires OBS Studio with WebSocket Server enabled
- Records the real display (HDMI/DisplayPort output)
- Perfect for production videos

### Headless Mode (Docker/Xvfb)
- **CI/CD friendly** — no display required
- Uses virtual X display (Xvfb)
- Captures screenshots at configurable FPS
- Lower quality than OBS but fully automated
- Good for testing and CI pipelines

```bash
# Start virtual display
Xvfb :99 -screen 0 1920x1080x24 &
DISPLAY=:99 python run.py --capture --all
```

---

## TTS Voice Options

| Engine      | Cost  | Quality  | Setup                        |
|-------------|-------|----------|------------------------------|
| edge-tts    | Free  | Good     | `pip install edge-tts`       |
| ElevenLabs  | Paid  | Excellent| API key + `pip install elevenlabs` |
| F5-TTS      | Free  | Excellent| Conda env + GPU recommended  |

Browse edge-tts voices:
```python
from toolkit.narrator import Narrator
n = Narrator({"engine": "edge-tts", "voice": "en-US-GuyNeural"})
voices = n.list_voices()
# Filter by locale: [v for v in voices if "en-" in v["Locale"]]
```

---

## Tips

- **Start with dry-run**: `--dry-run` shows what would happen without executing
- **Resume interrupted runs**: `--from N` to skip completed sequences
- **Cache narration**: TTS audio is cached — only regenerates if the file is missing
- **Debug timing**: Use `--verbose` to see detailed timing logs
- **Calibrate first**: Always calibrate before recording. `--live` mode helps.
