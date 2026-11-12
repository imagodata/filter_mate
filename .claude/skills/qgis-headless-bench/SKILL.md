---
name: qgis-headless-bench
description: Run the FilterMate checks in a real QGIS without a screen (Docker images qgis/qgis, Xvfb) - the GUI smoke, the agent tool and chat checks - and read their results. Use before merging a change of the dock, the agent or the configuration, or when a check must run in QGIS 3.22, LTR or latest.
---

# FilterMate in a real QGIS, headless

Never launch the QGIS of the user (it opens on their screen); run the official images in Docker.

## The GUI smoke (`tests/qgis_headless/run_gui_smoke.py`)

The dock with its own widgets, every layer kind, the agent settings steps. QGIS hangs before Python without a D-Bus
session bus on the Ubuntu 26.04 images, and the dock needs a 1600x1000 screen:

```bash
docker run --rm -v "$PWD:/src:ro" qgis/qgis:ltr bash -c \
  "python3 /src/tests/qgis_headless/make_fixtures.py /tmp/fm >/dev/null 2>&1; \
   FM_FIXTURES=/tmp/fm timeout 900 dbus-run-session -- xvfb-run -a -s '-screen 0 1600x1000x24' \
   qgis --nologo --noversioncheck --lang en --profiles-path /tmp/profiles \
   --code /src/tests/qgis_headless/run_gui_smoke.py" > gui_ltr.log 2>&1
grep -E '^(PASS|FAIL|XFAIL|SKIP)' gui_ltr.log | awk '{print $1}' | sort | uniq -c
```

- Images: `qgis/qgis:release-3_22`, `ltr`, `stable`, `latest` (Qt6). Run ltr and latest at least; 3.22 for an API
  that changed.
- About 12 minutes each; run them in the background, in parallel.
- A timeout with no output at all is the missing D-Bus or screen, not the change.
- The repository is mounted read only; the script copies the plugin. The plugin log may complain it cannot write:
  noise, not an error.

## Other checks

- `check_agent_tools.py`, `check_agent_chat.py`: `-e QT_QPA_PLATFORM=offscreen`, `qgis/qgis:ltr python3 ...` (see their
  docstrings); `check_agent_chat.py` replaces the dialogs, a modal one left would hang it.
- `scripts/agent_eval.py`: offline (no network), `--live` costs money: only with the user's go.
- Unit tests: `python3 -m pytest -q tests/unit -p no:cacheprovider` (no QGIS).

## Reading a failure

- Compare with main before blaming the change: `git archive origin/main | tar -x -C /tmp/main_src` and run the same
  image on it. A check can pass on main only because a later step repaired what an earlier one broke (2026-11-12: a
  change of theme left the section headers at 42 px; the UI_PROFILE step that followed hid it).
- Bisect a failing step by running variants in parallel (one change each) rather than one after the other.
- Steps share the dock: a step that leaves cards in the AGENT thread breaks the "welcome is shown" check; one that
  opens CONFIGURATION breaks "FILTERING open". Leave the dock as you found it.

## Pitfalls

- The scratchpad of a session is emptied when it restarts: keep bench scripts in the repository or recreate them.
- The isolated worktree guard refuses heredocs mixed with git in one command: write a script, then run it.
