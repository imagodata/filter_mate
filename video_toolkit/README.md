# Video Toolkit

**Automate high-quality tutorial videos of any desktop application.**

A batteries-included Python toolkit for creating professional tutorial videos
with synchronized narration, architecture diagrams, and precise UI automation —
without any manual editing.

---

## What This Toolkit Does

```
Your Python code ──► UI actions + narration cues
                         │
                         ├── OBS WebSocket  ──► records your screen (1080p/4K)
                         ├── edge-tts/ElevenLabs ──► generates voiceover
                         ├── Playwright  ──► renders Mermaid diagrams to PNG
                         └── FFmpeg  ──► assembles final video with synced audio
```

**Result:** A polished MP4 tutorial video where:
- The mouse moves naturally to UI elements
- Narration is synchronized to on-screen actions
- Architecture diagrams appear at the right moments
- Everything is reproducible — run it again to re-record

---

## Stack Overview

| Component | Library | Version | License |
|-----------|---------|---------|---------|
| Screen recording | OBS Studio / Xvfb | 30.x | GPL-2 |
| OBS API | obsws-python | ≥1.7 | MIT |
| UI automation | PyAutoGUI | ≥0.9 | BSD |
| TTS (free) | edge-tts | ≥6.1 | MIT |
| TTS (paid) | ElevenLabs | ≥1.0 | Commercial |
| TTS (clone) | F5-TTS | v1 | MIT |
| Diagram render | Playwright + Chromium | ≥1.42 | Apache-2 |
| Video assembly | FFmpeg | ≥6.0 | LGPL-2.1+ |
| CLI | Click | ≥8.1 | BSD |
| Config | PyYAML | ≥6.0 | MIT |
| Audio metadata | Mutagen | ≥1.47 | GPL-2 |

---

## Two Recording Modes

### 🖥️ Desktop Mode (OBS Studio)
Best for production-quality videos on a workstation.

```
Your Script ──► PyAutoGUI ──► moves mouse + types
                   │
OBS Studio ──────────────────────────────────────► records display
WebSocket API ◄── OBSController (start/stop/switch_scene)
```

- Hardware-accelerated encoding (NVENC, QuickSync, x264)
- Captures exact display output (hardware cursor, GPU effects)
- Requires OBS Studio running with WebSocket Server enabled

### 🐳 Headless Mode (Docker/Xvfb)
Best for CI/CD pipelines, servers, or unattended automation.

```
Xvfb :99 ──► virtual framebuffer (no physical display needed)
                   │
FrameCapturer ──── takes PNG screenshots at configurable FPS
                   │
FFmpeg ──────────► assembles frames into video
```

- No display required (runs inside Docker, GitHub Actions, WSL)
- Uses `import` (ImageMagick) or `scrot` for frame capture
- Same Python API as OBS mode — sequences work transparently

**Both modes use identical sequence code.** Switch with `--capture` flag.

---

## Installation

### Prerequisites

**All platforms:**
```bash
pip install -r requirements.txt
```

**FFmpeg** (required for video assembly):
```bash
# Windows (winget)
winget install Gyan.FFmpeg

# Linux (apt)
sudo apt install ffmpeg

# macOS (brew)
brew install ffmpeg
```

**OBS Studio** (desktop mode only):
- Download from https://obsproject.com
- Enable WebSocket Server: Tools > WebSocket Server Settings

**Headless mode** (Linux/Docker only):
```bash
sudo apt install xvfb imagemagick xdotool scrot
```

**Playwright** (for diagram PNG rendering):
```bash
pip install playwright
playwright install chromium
```

### Install as a package

```bash
# Editable install (recommended for development)
pip install -e .

# Or add to your project
pip install -e /path/to/video_toolkit
```

---

## Quick Start

### 1. Copy the example project

```bash
cp -r examples/my_app my_project/
cd my_project/
```

### 2. Configure

```bash
cp ../../config.template.yaml config.yaml
# Edit config.yaml: set window_title to your app's window name
```

### 3. Define your UI regions

```bash
# Start your application, then:
python ../../scripts/calibrate.py --config config.yaml
```

The calibration tool walks you through positioning the mouse on each
UI element. Coordinates are saved automatically to `config.yaml`.

```
  Calibrating group: Menu Bar Items
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  >> the FILE menu item in the menu bar
     Current: (0, 0)
     Position mouse on element, then press ENTER
     > [ENTER]
     + Recorded: (10, 28)
```

### 4. Set up OBS (desktop mode)

```bash
python ../../scripts/setup_obs.py --config config.yaml
```

Or use frame capture mode (no OBS needed):

```bash
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99
```

### 5. Preview without executing

```bash
python run.py --list         # List sequences and estimated durations
python run.py --dry-run --all  # Show what would happen
```

### 6. Generate assets

```bash
python run.py --diagrams     # Generate Mermaid diagram slides
python run.py --narration    # Pre-generate TTS narration audio
```

### 7. Record!

```bash
# Desktop mode (OBS):
python run.py --all

# Headless mode (Xvfb):
python run.py --capture --all

# Single sequence for testing:
python run.py --sequence 0
```

---

## Creating Your Own Project

### Project structure

```
my_project/
├── config.yaml           # Your app's config (from config.template.yaml)
├── automator.py          # AppAutomator subclass for your app
├── diagrams.py           # Mermaid diagram definitions (optional)
├── sequences/
│   ├── __init__.py       # SEQUENCES = [Seq0, Seq1, ...]
│   ├── intro.py          # Each sequence in its own file
│   └── demo.py
└── run.py                # CLI entry point
```

### Step 1: Create your automator

Subclass `AppAutomator` and add methods for every UI interaction:

```python
# automator.py
from toolkit.app_automator import AppAutomator

class MyAppAutomator(AppAutomator):
    """Automates My Application via PyAutoGUI."""

    def open_dashboard(self) -> None:
        """Click the Dashboard button in the sidebar."""
        self.click_region("sidebar_dashboard")
        self.wait(0.5)

    def search_for(self, query: str) -> None:
        """Type in the search bar and press Enter."""
        self.click_region("search_bar")
        self.clear_field()
        self.type_text_unicode(query)
        self.press_key("return")
        self.wait(1.0)

    def select_item(self, index: int) -> None:
        """Select an item from the results list using keyboard navigation."""
        self.click_region("results_list")
        self.press_key("home")
        for _ in range(index):
            self.press_key("down")
        self.press_key("return")
        self.wait(self.timing.get("action_pause", 1.0))
```

> **Note:** Region names (e.g. `"sidebar_dashboard"`) must be calibrated
> in `config.yaml` using `calibrate.py`.

### Step 2: Define your regions

Edit the `GROUPS` dict in `scripts/calibrate.py` to describe your app's UI:

```python
# scripts/calibrate.py (copy from video_toolkit/scripts/ and customize)

GROUPS = {
    "main_window": {
        "label": "Main Application Window",
        "desc": "The primary window boundary",
        "targets": [
            ("main_window", "TOP-LEFT corner of the main window", "tl"),
            ("main_window", "BOTTOM-RIGHT corner of the main window", "br"),
        ],
    },
    "sidebar": {
        "label": "Sidebar Navigation",
        "desc": "Navigation sidebar buttons",
        "targets": [
            ("sidebar_dashboard", "the DASHBOARD button", "point"),
            ("sidebar_settings", "the SETTINGS button", "point"),
            ("sidebar_help", "the HELP button", "point"),
        ],
    },
    "search": {
        "label": "Search Bar",
        "desc": "The main search input",
        "targets": [
            ("search_bar", "the SEARCH INPUT field", "point"),
            ("results_list", "the RESULTS LIST area", "tl"),
            ("results_list", "the RESULTS LIST area (bottom)", "br"),
        ],
    },
}
```

### Step 3: Write sequences

**Simple sequences** (VideoSequence — manual timing):

```python
# sequences/intro.py
from toolkit.sequence import VideoSequence

class IntroSequence(VideoSequence):
    name = "Introduction"
    sequence_id = "seq00_intro"
    duration_estimate = 15.0
    narration_text = "Welcome to My App. In this tutorial..."
    obs_scene = "App Fullscreen"

    def execute(self, recorder, app, config):
        app.focus_window()
        app.wait(2.0)
        app.open_dashboard()
        app.wait(3.0)
        # Show a diagram
        self.show_diagram(recorder, "architecture", duration=5.0)
```

**Narration-synchronized sequences** (TimelineSequence — precise timing):

```python
# sequences/demo.py
from toolkit.sequence import TimelineSequence
from toolkit.timeline import NarrationCue

class DemoSequence(TimelineSequence):
    name = "Demo — Search Feature"
    sequence_id = "seq01_demo"

    def build_timeline(self, recorder, app, config):
        return [
            NarrationCue(
                text="Let's start by searching for a record.",
                actions=lambda: app.open_dashboard(),
                post_delay=0.5,
            ),
            NarrationCue(
                text="Type your search query in the search bar.",
                actions=lambda: app.search_for("example query"),
                sync="during",   # narration plays while action runs
                post_delay=1.0,
            ),
            NarrationCue(
                text="The results appear instantly.",
                actions=lambda: app.wait(2.0),
                sync="during",
            ),
            NarrationCue(
                text="Click the first result to open it.",
                actions=lambda: app.select_item(0),
                sync="before",   # click FIRST, then narration plays
                post_delay=1.5,
            ),
        ]
```

### Step 4: Register and run

```python
# sequences/__init__.py
from .intro import IntroSequence
from .demo import DemoSequence

SEQUENCES = [IntroSequence, DemoSequence]
```

```python
# run.py
from pathlib import Path
from toolkit.cli import make_cli
from automator import MyAppAutomator
from sequences import SEQUENCES

cli = make_cli(
    project_name="My App Tutorial",
    config_path=Path("config.yaml"),
    sequences=SEQUENCES,
    automator_factory=lambda cfg: MyAppAutomator(cfg),
)

if __name__ == "__main__":
    cli()
```

---

## Configuration Reference

### `app` section

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `window_title` | str | `""` | Title substring to identify app window |
| `app_name` | str | `""` | Display name for diagrams/slides |
| `app_version` | str | `""` | Version shown in diagram headers |
| `assets_dir` | str | `"assets/buttons"` | Directory for button image templates |
| `regions` | dict | `{}` | Calibrated UI element positions |

### `timing` section

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `click_delay` | float | `0.3` | PyAutoGUI global PAUSE between actions |
| `type_delay` | float | `0.05` | Delay between keystrokes |
| `scroll_delay` | float | `0.2` | Delay between scroll ticks |
| `action_pause` | float | `1.0` | Pause after significant actions |
| `transition_pause` | float | `2.0` | Pause at sequence start/end |
| `mouse_move_duration` | float | `0.5` | Mouse movement duration (smooth) |
| `startup_wait` | float | `3.0` | Wait after focusing the app window |

### `obs` section

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `host` | str | `"localhost"` | OBS WebSocket host |
| `port` | int | `4455` | OBS WebSocket port |
| `password` | str | `""` | OBS WebSocket password |
| `scenes` | dict | | Scene name mapping |
| `output_dir` | str | `~/Videos` | OBS recording output directory |

### `narration` section

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `engine` | str | `"edge-tts"` | TTS engine: `edge-tts`, `elevenlabs`, `f5-tts` |
| `voice` | str | `"en-US-GuyNeural"` | Voice name (engine-dependent) |
| `output_dir` | str | `"output/narration"` | Audio cache directory |
| `speed` | str | `"+0%"` | Speed adjustment for edge-tts: `+10%`, `-5%` |

### `diagrams` section

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `output_dir` | str | `"output/diagrams"` | HTML/PNG output directory |
| `width` | int | `1920` | Viewport width for rendering |
| `height` | int | `1080` | Viewport height for rendering |
| `theme` | str | `"dark"` | Mermaid theme |
| `background_color` | str | `"#1a1a2e"` | Background gradient color |
| `accent_color` | str | `"#4CAF50"` | Accent color for borders |

### `output` section

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `final_dir` | str | `"output/final"` | Final video output directory |
| `resolution` | str | `"1920x1080"` | Output resolution |
| `fps` | int | `30` | Output frame rate |
| `codec` | str | `"libx264"` | FFmpeg video codec |
| `quality` | str | `"23"` | CRF quality value |

---

## API Reference

### AppAutomator

Base class for app automation. Subclass for your specific application.

```python
class AppAutomator:
    def focus_window()                          # Bring app to foreground
    def click_region(name, offset_x=0, offset_y=0)  # Click calibrated region
    def double_click_region(name)              # Double-click region
    def right_click_region(name)               # Right-click region
    def click_at(x, y)                          # Click at coordinates
    def click_image(name, confidence=0.85)     # Click by image template
    def type_text(text, interval=None)          # Type ASCII text
    def type_text_unicode(text)                # Paste unicode via clipboard
    def hotkey(*keys)                           # Keyboard shortcut (e.g. ctrl+z)
    def press_key(key, presses=1)               # Press a key
    def move_to(x, y, duration=None)            # Smooth mouse movement
    def scroll(clicks, direction="down")        # Scroll mouse wheel
    def drag(start_x, start_y, end_x, end_y)   # Drag operation
    def highlight(region, duration=2.0)         # Visual attention circle
    def hover(region, duration=1.5)             # Hover without clicking
    def wait(seconds)                           # Timed pause
    def screenshot(path)                        # Full-screen capture
    def clear_field()                           # Ctrl+A, Delete
    def close_dialog()                          # Escape key
    def confirm_dialog()                        # Enter key
    def undo()                                  # Ctrl+Z
    def redo()                                  # Ctrl+Y
    def save()                                  # Ctrl+S
```

### VideoSequence

```python
class VideoSequence(ABC):
    name: str               # Human-readable name
    sequence_id: str        # Short identifier (e.g. "seq00")
    duration_estimate: float # Estimated duration in seconds
    narration_text: str     # Full narration text (for TTS generation)
    obs_scene: str          # OBS scene name to activate

    def setup(recorder, app, config)     # Called before recording
    def execute(recorder, app, config)   # Main automation (implement this)
    def teardown(recorder, app, config)  # Called after recording
    def run(recorder, app, config)       # Runs setup + execute + teardown
    def show_diagram(recorder, id, duration)  # Show diagram overlay
    def elapsed()                        # Seconds since sequence started
```

### TimelineSequence

```python
class TimelineSequence(VideoSequence):
    play_audio: bool    # Play narration through speakers during recording

    def build_timeline(recorder, app, config) -> list[NarrationCue]
    # Implement this instead of execute()
```

### NarrationCue

```python
@dataclass
class NarrationCue:
    text: str                  # Narration text (empty = silent pause)
    actions: Callable | None   # UI actions to execute
    sync: str                  # "during" | "after" | "before"
    pre_delay: float           # Seconds to wait before this cue
    post_delay: float          # Seconds to wait after this cue
    scene: str | None          # Switch to this scene before the cue
    label: str                 # Human-readable label for logging
```

### OBSController / FrameCapturer

Both implement the same interface:

```python
with recorder:              # Context manager (connect/disconnect)
    recorder.start_recording()
    recorder.wait_for_recording_start()
    recorder.switch_scene(name)
    recorder.show_diagram_overlay(visible=True)
    recorder.pause_recording()
    recorder.resume_recording()
    path = recorder.stop_recording()  # Returns output file path
    recorder.take_screenshot(...)
```

### VideoAssembler

```python
assembler = VideoAssembler(config["output"])
assembler.remux_mkv_to_mp4(mkv_path)
assembler.add_narration(video, narration, output, narration_volume=1.0)
assembler.add_intro_outro(video, intro, outro, output)
assembler.combine_recording_with_diagrams(video, diagrams, timestamps, output)
assembler.create_final_video(clips, narrations, output_path)
assembler.create_final_video_with_timecodes(clips, timeline_results, output_path)
```

### DiagramGenerator

```python
gen = DiagramGenerator(config["diagrams"])
html_path = gen.generate_diagram(mermaid_code, output_path, title="...")
png_path = gen.render_to_png(html_path, png_path)
html_paths = gen.generate_all_diagrams(definitions, output_dir)
png_paths = gen.render_all_to_png(html_paths, output_dir)
```

### Narrator

```python
narrator = Narrator(config["narration"])
path = narrator.generate_narration(text, output_path, voice=None)
paths = narrator.generate_all_narrations(script_dict, output_dir)
duration = narrator.get_narration_duration(audio_path)
voices = narrator.list_voices()  # edge-tts only
```

---

## TTS Voices Reference

### edge-tts (free, 400+ voices)

```python
# List voices programmatically
from toolkit.narrator import Narrator
n = Narrator({"engine": "edge-tts", "voice": "en-US-GuyNeural"})
voices = n.list_voices()

# Filter by language
english = [v for v in voices if "en-" in v["Locale"]]
french = [v for v in voices if "fr-" in v["Locale"]]
```

Recommended English voices:
- `en-US-GuyNeural` — Male, neutral American
- `en-US-JennyNeural` — Female, friendly American
- `en-US-AriaNeural` — Female, natural American
- `en-GB-RyanNeural` — Male, British
- `en-AU-NatashaNeural` — Female, Australian

Speed control: `speed: "+10%"` (faster) or `speed: "-15%"` (slower)

### ElevenLabs (paid, high quality)

```bash
export ELEVENLABS_API_KEY="your-api-key"
```

```yaml
narration:
  engine: elevenlabs
  voice: "Adam"  # or use voice ID from ElevenLabs dashboard
```

### F5-TTS (free, voice cloning)

Clones any voice from a ~15-30 second audio sample.

Setup:
```bash
conda create -n f5-tts python=3.11 -y
conda activate f5-tts
pip install f5-tts torch torchaudio
```

Config:
```yaml
narration:
  engine: f5-tts
  f5_ref_audio: output/narration/ref_voice.wav  # Your voice sample
  f5_ref_text: "Exact transcript of the reference audio"
  f5_conda_env: f5-tts
```

---

## FFmpeg Commands Reference

These are the FFmpeg pipelines used internally:

**Remux MKV to MP4 (lossless):**
```bash
ffmpeg -i recording.mkv -c copy output.mp4
```

**Concatenate clips:**
```bash
ffmpeg -f concat -safe 0 -i filelist.txt -c copy output.mp4
```

**Mix narration with video:**
```bash
ffmpeg -i video.mp4 -i narration.mp3 \
  -filter_complex "[0:a]volume=0.3[orig];[1:a]volume=1.0[narr];[orig][narr]amix=inputs=2:duration=first:normalize=0[aout]" \
  -map 0:v -map [aout] -c:v copy -c:a aac -b:a 192k output.mp4
```

**Final encode:**
```bash
ffmpeg -i input.mp4 -c:v libx264 -crf 23 -preset slow \
  -c:a aac -b:a 192k -movflags +faststart \
  -vf scale=1920:1080 -r 30 final.mp4
```

**Precise narration placement with timecodes:**
```bash
ffmpeg -f lavfi -t 300 -i anullsrc=r=44100:cl=stereo \
  -i seg0.mp3 -i seg1.mp3 \
  -filter_complex "[1:a]adelay=5000|5000[s0];[2:a]adelay=18000|18000[s1];[0:a][s0][s1]amix=inputs=3:normalize=0[aout]" \
  -map [aout] -c:a pcm_s16le narration_track.wav
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Video Toolkit                           │
│                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────────┐  │
│  │ VideoSequence│   │TimelineSeq.  │   │  AppAutomator  │  │
│  │ (manual)     │   │ (narr-synced)│   │  (generic base)│  │
│  └──────┬───────┘   └──────┬───────┘   └───────┬────────┘  │
│         │                  │                   │           │
│         └──────────────────┼───────────────────┘           │
│                            │ execute(recorder, app, config) │
│                            ▼                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Recording Backend                      │   │
│  │  OBSController          FrameCapturer               │   │
│  │  (desktop + OBS)        (headless + Xvfb)           │   │
│  │  Same interface ─────────────────────────►          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌────────────┐   ┌─────────────┐   ┌──────────────────┐   │
│  │  Narrator  │   │  Timeline   │   │DiagramGenerator  │   │
│  │  edge-tts  │   │  Executor   │   │ Mermaid → PNG    │   │
│  │  ElevenLabs│   │  NarrCue    │   │ Playwright       │   │
│  │  F5-TTS    │   │  sync modes │   │                  │   │
│  └────────────┘   └─────────────┘   └──────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              VideoAssembler (FFmpeg)                 │   │
│  │  concat clips → mix narration → encode final MP4    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

### OBS connection failed
- Ensure OBS Studio is running
- Enable WebSocket: Tools > WebSocket Server Settings > Enable
- Check host/port in config.yaml match OBS settings
- If password is set in OBS, set it in config.yaml too

### PyAutoGUI FailSafeException
- Mouse moved to top-left corner (safety mechanism)
- Move mouse away from corner to continue
- Reduce `mouse_move_duration` if moves are too slow

### Window not found / focus failed
- Check `window_title` in config.yaml matches the actual window title
- Use `--live` in calibrate.py to find exact coordinates
- On Linux: ensure `xdotool` is installed

### Narration audio missing / empty
- edge-tts requires internet connection
- Check the voice name is valid: `python -c "from toolkit.narrator import Narrator; n=Narrator({'engine':'edge-tts','voice':'en-US-GuyNeural'}); print(n.list_voices()[:3])"`
- For ElevenLabs: check `ELEVENLABS_API_KEY` is set

### Diagram PNG not generated
- Install Playwright: `pip install playwright && playwright install chromium`
- On Linux headless: ensure a display is available (Xvfb)

### FFmpeg errors
- Check FFmpeg version: `ffmpeg -version` (requires ≥ 4.0)
- Ensure input files exist before assembly
- Check disk space for output files

### Headless capture too slow
- Increase `capture.fps` (at cost of disk space)
- Use `method: ffmpeg` instead of `import` for faster capture
- Reduce `capture.resolution` if not doing 4K

### Unicode text not typing correctly
- Use `type_text_unicode()` instead of `type_text()` for non-ASCII
- Requires `pyperclip`: `pip install pyperclip`
- On Linux: install `xclip` or `xsel`

---

## License

MIT License — see LICENSE file.

---

## Contributing

Contributions welcome! Please:
1. Add tests for new features
2. Update this README for new components
3. Keep the example project working
4. Follow the existing code style

---

*Built for automating tutorial video production. Extracted and generalized
from a QGIS plugin video automation project.*
