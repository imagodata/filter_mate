# -*- coding: utf-8 -*-
"""Retake the screenshots of the agent settings used by the user guide (website/img/guide/agent-settings*.png).

The real AgentSettingsDialog is opened in a real QGIS, without a screen: Provider tab, Claude (Anthropic) with its
default model, no key typed, the consent unticked. One image in English, one in French (the translations of
i18n/FilterMate_fr.qm). Run it in a QGIS image, on a writable copy of the repository:

    docker run --rm --network none -v "$PWD:/src:ro" -e FM_REPO=/tmp/copy -e FM_OUT=/tmp/out qgis/qgis:ltr bash -c \\
        'mkdir /tmp/copy /tmp/out; cp -r /src/. /tmp/copy; \\
         dbus-run-session -- xvfb-run -a -s "-screen 0 1600x1000x24" python3 /tmp/copy/scripts/agent_settings_screenshot.py'

then copy /tmp/out/agent-settings.png and agent-settings-fr.png to website/img/guide/. The sizes are those of the
images of the guide (English 712x660, French 766x660): the French text is wider.
"""
import os
import sys
import tempfile

HOME = tempfile.mkdtemp()
os.environ["QGIS_CUSTOM_CONFIG_PATH"] = HOME
os.environ["QGIS_AUTH_DB_DIR_PATH"] = HOME  # no stored key, no stored consent: the dialog opens as on a first run

from qgis.core import QgsApplication  # noqa: E402
from qgis.PyQt.QtCore import QCoreApplication, QLibraryInfo, QTranslator  # noqa: E402

SHOTS = (("agent-settings.png", None, 712), ("agent-settings-fr.png", "fr", 766))
HEIGHT = 660


def shoot(out_dir, repo, file_name, lang, width):
    from filter_mate.adapters.agent.settings import AgentSettings, target_of
    from filter_mate.ui.widgets.agent_panel import AgentSettingsDialog

    translators = []
    if lang:
        translator = QTranslator()
        if not translator.load(os.path.join(repo, "i18n", f"FilterMate_{lang}.qm")):
            raise RuntimeError(f"cannot load the {lang} catalog")
        translators.append(translator)
        # The buttons Save / Cancel are Qt's own: its catalog, when the image has it, translates them as QGIS does.
        qt_translator = QTranslator()
        if qt_translator.load(f"qtbase_{lang}", QLibraryInfo.location(QLibraryInfo.LibraryLocation.TranslationsPath)):
            translators.append(qt_translator)
        for item in translators:
            QCoreApplication.installTranslator(item)
    dialog = AgentSettingsDialog(AgentSettings(preset="anthropic", model="claude-haiku-5-5"), target_of, None)
    dialog.tabs.setCurrentIndex(0)
    dialog.resize(width, HEIGHT)
    dialog.show()
    for _ in range(5):
        QCoreApplication.processEvents()
    assert not dialog.key.text() and not dialog.consent.isChecked()
    path = os.path.join(out_dir, file_name)
    dialog.grab().save(path, "PNG")
    print(path, dialog.size().width(), dialog.size().height(), flush=True)
    dialog.close()
    for item in translators:
        QCoreApplication.removeTranslator(item)


if __name__ == "__main__":
    app = QgsApplication([], True)
    app.initQgis()
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    repo = os.environ.get("FM_REPO", here)
    out = os.environ.get("FM_OUT", os.path.join(repo, "website", "img", "guide"))
    package_root = tempfile.mkdtemp()
    os.symlink(repo, os.path.join(package_root, "filter_mate"))
    sys.path.insert(0, package_root)
    sys.dont_write_bytecode = True
    status = 0
    try:
        for shot in SHOTS:
            shoot(out, repo, *shot)
    except Exception:
        import traceback
        traceback.print_exc()
        status = 1
    os._exit(status)
