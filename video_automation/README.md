# FilterMate Video Automation

Automates the production of the FilterMate QGIS plugin presentation video.

**Stack:** Python · PyAutoGUI · OBS WebSocket · edge-tts · FFmpeg · Playwright · Mermaid.js

---

## What It Does

| Step | Tool | Output |
|------|------|--------|
| Generate diagram slides | Mermaid + Playwright | `output/diagrams/*.html` + `*.png` |
| Generate narration audio | edge-tts / ElevenLabs | `output/narration/seq*.mp3` |
| Calibrate QGIS UI positions | Interactive CLI | `config.yaml` updated |
| Configure OBS | OBS WebSocket 5 | Scenes + sources ready |
| Record sequences 0–10 | PyAutoGUI + OBS | MKV clips per sequence |
| Assemble final video | FFmpeg | `output/final/filtermate_final.mp4` |

---

## Prerequisites

| Requirement | Version | Notes |
|------------|---------|-------|
| Python | 3.10+ | |
| QGIS | 3.x / 4.x | With FilterMate plugin loaded |
| OBS Studio | 28+ | With WebSocket Server enabled |
| FFmpeg | 5+ | Must be on `PATH` |
| Windows | 10/11 | For PyAutoGUI + win32gui focus |

### Install Python dependencies

```bash
cd video_automation
pip install -r requirements.txt
```

For PNG diagram rendering (optional but recommended):

```bash
pip install playwright
playwright install chromium
```

---

## Quick Start

### 1. Configure

Edit `config.yaml`:

```yaml
obs:
  password: "your-obs-websocket-password"   # Tools → WebSocket Server Settings
  output_dir: "C:/Users/YourName/Videos/FilterMate"

narration:
  voice: "fr-FR-HenriNeural"   # or change to a different locale/voice
```

### 2. Generate Diagram Slides

```bash
python run.py --diagrams
```

This generates `output/diagrams/01_positioning.html` … `12_metrics.html`
and (if Playwright is installed) matching PNG files.

### 3. Generate Narration Audio

```bash
python run.py --narration
```

Generates `output/narration/seq00_narration.mp3` … `seq10_narration.mp3`
using Microsoft Edge TTS (no API key required).

To use ElevenLabs instead:

```yaml
# config.yaml
narration:
  engine: "elevenlabs"
  voice: "YOUR_VOICE_ID"
```

```bash
set ELEVENLABS_API_KEY=sk-...
python run.py --narration
```

### 4. Calibrate QGIS UI Positions

Run with QGIS open and FilterMate visible:

```bash
python run.py --calibrate
```

Follow the prompts to click on each UI element. Coordinates are saved to `config.yaml`.

Check your calibration at any time:

```bash
python scripts/calibrate.py --list
```

### 5. Configure OBS

Ensure OBS is running with the WebSocket Server enabled (`Tools → WebSocket Server Settings → Enable`), then:

```bash
python run.py --setup-obs
```

This creates all required scenes:
- **QGIS Fullscreen** — Main recording scene
- **QGIS + FilterMate** — QGIS with FilterMate dock visible
- **Diagram Overlay** — Browser source for Mermaid HTML diagrams
- **Intro** / **Outro** — Title cards

### 6. Record Sequences

**Full production run** (all 11 sequences, ~10 minutes):

```bash
python run.py --all
```

**Single sequence** (useful for re-takes):

```bash
python run.py --sequence 4    # Filtering demo — the big one
```

**Preview without executing** (check timing, scenes, steps):

```bash
python run.py --all --dry-run
```

### 7. Assemble Final Video

```bash
python run.py --assemble
```

This runs the FFmpeg pipeline:
1. Concatenates all sequence clips
2. Mixes narration audio
3. Encodes final MP4 (`output/final/filtermate_final.mp4`)

---

## Directory Structure

```
video_automation/
├── README.md                    ← you are here
├── requirements.txt
├── config.yaml                  ← all configuration
├── run.py                       ← main CLI
│
├── core/
│   ├── obs_controller.py        ← OBS WebSocket 5 control
│   ├── qgis_automator.py        ← PyAutoGUI QGIS interaction
│   ├── diagram_generator.py     ← Mermaid → HTML/PNG
│   ├── narrator.py              ← edge-tts / ElevenLabs TTS
│   └── video_assembler.py       ← FFmpeg post-production
│
├── sequences/
│   ├── base.py                  ← VideoSequence base class
│   ├── seq00_intro.py           ← Intro + Hook (0:20)
│   ├── seq01_problem.py         ← Le Problème (0:45)
│   ├── seq02_install.py         ← Installation (0:30)
│   ├── seq03_interface.py       ← Interface Vue d'ensemble (0:45)
│   ├── seq04_filtering_demo.py  ← Filtrage Demo LIVE (2:00) ★
│   ├── seq05_exploration.py     ← Exploration (1:00)
│   ├── seq06_export.py          ← Export GeoPackage (1:00)
│   ├── seq07_backends.py        ← Multi-backend (0:45)
│   ├── seq08_architecture.py    ← Architecture Hexagonale (0:45)
│   ├── seq09_advanced.py        ← Fonctionnalités Avancées (0:45)
│   └── seq10_conclusion.py      ← Conclusion + CTA (0:20)
│
├── diagrams/
│   ├── template.html            ← dark-theme HTML template (1920×1080)
│   └── mermaid_definitions.py   ← all 12 Mermaid diagrams
│
├── scripts/
│   ├── calibrate.py             ← interactive calibration tool
│   └── setup_obs.py             ← OBS auto-configuration
│
├── assets/
│   └── buttons/                 ← button screenshot images for image-based clicking
│                                   (create manually: take screenshots of each button)
│
└── output/
    ├── diagrams/                ← generated HTML + PNG diagram slides
    ├── narration/               ← generated MP3 narration files
    └── final/                   ← final assembled video
```

---

## Sequence Timing

| # | Sequence | Est. Duration |
|---|----------|--------------|
| 0 | Intro + Hook | 0:20 |
| 1 | Le Problème | 0:45 |
| 2 | Installation | 0:30 |
| 3 | Interface | 0:45 |
| 4 | Filtrage Demo ★ | 2:00 |
| 5 | Exploration | 1:00 |
| 6 | Export GeoPackage | 1:00 |
| 7 | Multi-backend | 0:45 |
| 8 | Architecture | 0:45 |
| 9 | Fonctionnalités Avancées | 0:45 |
| 10 | Conclusion + CTA | 0:20 |
| | **TOTAL** | **~9:55** |

---

## Available Voices (edge-tts)

French voices — no API key required:

| Voice ID | Style |
|----------|-------|
| `fr-FR-HenriNeural` | Male, neutral ← default |
| `fr-FR-DeniseNeural` | Female, neutral |
| `fr-FR-EloiseNeural` | Female, friendly |
| `fr-BE-CharlineNeural` | Female, Belgian FR |

List all French voices:

```bash
edge-tts --list-voices | grep "fr-"
```

---

## Button Assets

The automation uses image recognition for buttons that aren't in fixed positions.
Create screenshots with:

```bash
# Take a screenshot of a button and save to assets/buttons/
python -c "
import pyautogui, time
time.sleep(3)  # Position mouse first
x, y = pyautogui.position()
region = pyautogui.screenshot(region=(x-30, y-15, 60, 30))
region.save('assets/buttons/btn_filter.png')
"
```

Required button images:
- `btn_filter.png` — the green Filter button
- `btn_undo.png` — Undo button  
- `btn_redo.png` — Redo button
- `btn_unfilter.png` — Remove Filter button
- `btn_favorites.png` — Favorites/star button
- `btn_next_feature.png` — Next feature arrow (Exploring tab)
- `btn_pixel_picker.png` — Pixel Picker tool
- `btn_rectangle_range.png` — Rectangle Range tool
- `btn_sync_histogram.png` — Sync Histogram tool
- `btn_all_bands.png` — All Bands Info tool
- `btn_reset_range.png` — Reset Range tool
- `btn_select_all_layers.png` — Select All Layers (Export tab)
- `btn_export_gpkg.png` — Export GeoPackage button

---

## Troubleshooting

### OBS Connection Refused
- Ensure OBS is running
- Enable WebSocket: `Tools → WebSocket Server Settings → Enable WebSocket Server`
- Check port matches `config.yaml` (default: 4455)
- Check password matches

### PyAutoGUI Clicks Wrong Position
- Re-run calibration: `python run.py --calibrate`
- Ensure display scaling is 100% (or account for DPI scaling)
- Ensure QGIS is on the primary monitor in its normal position

### QGIS Window Not Found
- Check `config.yaml → qgis.window_title` matches your QGIS window title exactly
- Install pywin32: `pip install pywin32`

### Mermaid Diagrams Not Rendering as PNG
- Install Playwright: `pip install playwright && playwright install chromium`
- Check that the HTML files render correctly in a browser first

### FFmpeg Errors
- Ensure FFmpeg is on `PATH`: `ffmpeg -version`
- Download from https://ffmpeg.org/download.html
- On Windows, add to PATH: `setx PATH "%PATH%;C:\ffmpeg\bin"`

### Audio Duration = 0
- Install mutagen: `pip install mutagen`
- Or ensure ffprobe (part of FFmpeg) is on PATH

---

## Links

- **FilterMate GitHub:** https://github.com/imagodata/filter_mate
- **QGIS Plugin Store:** https://plugins.qgis.org/plugins/filter_mate  
- **Documentation:** https://imagodata.github.io/filter_mate
- **OBS WebSocket:** https://github.com/obsproject/obs-websocket
- **obsws-python:** https://github.com/aatikturk/obsws-python
- **edge-tts:** https://github.com/rany2/edge-tts
