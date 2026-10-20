# Contributing to FilterMate

FilterMate is a QGIS plugin (QGIS 3.22 to 4.x, Qt5 and Qt6). This page covers what you need to change the code and get a pull request merged. The source tree is described in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Reporting a bug

Open an issue at <https://github.com/imagodata/filter_mate/issues>. Give the FilterMate and QGIS versions, the operating system, the data source (PostgreSQL, GeoPackage, Shapefile, raster, point cloud), the steps, and the relevant lines of the FilterMate log or of QGIS's Log Messages panel.

## Environment

The unit tests run without QGIS: `tests/conftest.py` replaces the `qgis.*` modules with mocks.

```bash
python -m pip install -r requirements-test.txt     # pytest, pytest-cov, pytest-mock
python -m pytest tests/ -v -o "addopts="
```

CI (`.github/workflows/test.yml`) runs flake8 and the tests on Python 3.10 and 3.12. Use one of them locally. `-o "addopts="` drops the `addopts` of `pytest.ini`, as in CI.

Lint the plugin code with the CI command:

```bash
pip install flake8
python -m flake8 --extend-exclude=tests,scripts,website,docs --count
```

The REST API tests in `tests/api/` are skipped when `fastapi` is missing. CI does not install it; to run them, also install `requirements-api.txt`.

## Tests in a real QGIS

Mocks cannot show what QGIS does, so the scripts in `tests/qgis_headless/` run inside the official QGIS Docker images. They are not pytest modules. The header of `.github/workflows/qgis-headless.yml` has the commands; from the repository root:

```bash
# Engine: Processing and the public API on synthetic data
docker run --rm -v "$PWD:/src:ro" qgis/qgis:ltr bash -c \
  'python3 /src/tests/qgis_headless/make_fixtures.py /tmp/fm && python3 /src/tests/qgis_headless/run_smoke.py /tmp/fm'

# Dock: QGIS with its GUI under Xvfb
docker run --rm -v "$PWD:/src:ro" -e FM_FIXTURES=/tmp/fm qgis/qgis:ltr bash -c \
  'python3 /src/tests/qgis_headless/make_fixtures.py /tmp/fm && xvfb-run -a qgis --nologo --noversioncheck \
   --profiles-path /tmp/profiles --code /src/tests/qgis_headless/run_gui_smoke.py'
```

Each check prints `PASS`, `FAIL`, `SKIP` or `XFAIL`; only `FAIL` fails the run. CI runs the scripts on QGIS 3.22, 3.28, 3.34, 3.44 (with and without PDAL), 4.2 and the nightly image. Run them when you touch the dock, the coverage code (`adapters/qgis/coverage_layers/`) or anything that loads at plugin start.

## Code rules

- Python 3.10 or later, PEP 8, Google-style docstrings. flake8 is configured in `.flake8` (line length 200).
- Import Qt through `qgis.PyQt`, never `PyQt5` or `PyQt6` directly.
- Qt5/Qt6 and old QGIS versions are protected by tests that parse the source (AST) and fail on a known bad pattern. They apply to the whole plugin:
  - `tests/test_no_unscoped_qt_enums.py`: use scoped enums (`Qt.ItemDataRole.UserRole`, not `Qt.UserRole`).
  - `tests/test_no_qtwidgets_relocated_symbols.py`: `QAction`, `QShortcut` and the other classes moved to `QtGui` in Qt6 are imported from `QtGui` with a `QtWidgets` fallback in `except ImportError`.
  - `tests/test_no_unguarded_sip_import.py`: `import sip` sits in a `try`.
  - `tests/test_no_bare_disconnect_on_qgis_signals.py`: disconnect your own slot, not every receiver of a QGIS signal.
  - `tests/test_no_clear_on_map_layer_combobox.py`: do not call `clear()` on `QgsMapLayerComboBox`.
  - `tests/test_no_layout_insert_item_temporaries.py`: use `insertSpacerItem` or `addItem` for spacers.
  - `tests/test_package_import_exports.py`: a name imported from a plugin package must exist in its `__init__.py`.
- Call `setSubsetString` on the main thread only. A `QgsTask` queues subset requests and applies them in `finished()`.
- The plugin must load on QGIS 3.22 (see `metadata.txt`). Check a new QGIS API against the oldest version, or let the headless job do it.
- Add a test with a fix, as the guards above do. Put it under `tests/unit/` next to the module's tests; a bug that only a real QGIS shows goes into a `tests/qgis_headless/` script.

## Translations

Strings shown to users go through `tr()` or `QCoreApplication.translate`. `i18n/FilterMate.pro` lists the source files and the 34 `FilterMate_<locale>.ts` files; the compiled `.qm` files are committed. When you add a file with translatable strings, add it to the `SOURCES` of `FilterMate.pro`. Update the `.ts` files with Qt's `pylupdate` and compile them with `lrelease` (the repository has no script for it), and commit both `.ts` and `.qm`.

## Building the zip

```bash
bash scripts/prepare_plugin_zip.sh
```

It reads the version from `metadata.txt` and writes `dist/filter_mate_v<VERSION>.zip` without tests, scripts, website, `.ts` files and development folders. Releases are made by pushing a `v<version>` tag; `.github/workflows/release.yml` checks the tag against `metadata.txt`, tests, builds the zip and publishes. The release job also runs `scripts/publish_qgis.py <zip> --validate-only`, which scans the unpacked zip with Bandit and detect-secrets (what plugins.qgis.org blocks a version for, whatever the severity; B404 `import subprocess` is not counted). Run it before tagging; it uses the installed tools, else `uvx`, else `pip --target`. Accept a false positive with `# nosec Bxxx - reason` or `# pragma: allowlist secret`, never by skipping the scan. Describe user-visible changes in `CHANGELOG.md`.

## Commits and pull requests

- Branch from `main`; pull requests target `main` and are merged with a merge commit once CI is green.
- Write the commit subject in English, as a sentence about the behaviour, not the diff. The history reads, for example, "A removed layer no longer breaks the panel update, and its history goes too" and "REST API: web pages can no longer drive QGIS through the browser". A short prefix for an area is fine (`i18n:`, `Favorites sharing:`).
- Keep one subject per commit. Explain the cause in the body when the fix is not obvious.
- In the pull request, say what a user sees before and after, and how you tested (unit tests, headless run, real QGIS version).
