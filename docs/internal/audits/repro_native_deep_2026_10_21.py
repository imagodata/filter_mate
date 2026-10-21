"""Run the native audit regression checks from the maintained headless test suite."""
import pathlib
import runpy

if __name__ == "__main__":
    root = pathlib.Path(__file__).resolve().parents[3]
    runpy.run_path(str(root / "tests/qgis_headless/check_export_task_safety.py"), run_name="__main__")
