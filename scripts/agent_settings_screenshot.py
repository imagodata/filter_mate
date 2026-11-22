# -*- coding: utf-8 -*-
"""Retake the screenshots of the agent settings used by the user guide (website/img/guide/agent-settings*.png).

The real AgentSettingsDialog is opened in a real QGIS, without a screen: Provider tab, Claude (Anthropic) with its
default model, no key typed, the consent unticked. One image in English, one in French (the translations of
i18n/FilterMate_fr.qm). TAB_SHOTS adds the pages of the guide that had no picture (20 November 2026): the Sources
tab with three sources ticked, the Autonomy tab, the Other applications tab with the MCP server on, and the dialog
that asks before the agent follows a skill of the team. Run it in a QGIS image, on a writable copy of the repository:

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
from qgis.PyQt.QtCore import QCoreApplication, QLibraryInfo, QTimer, QTranslator, Qt  # noqa: E402
from qgis.PyQt.QtWidgets import QApplication, QSizePolicy  # noqa: E402


def translations_path():
    """Where Qt keeps its own catalogs: ``path`` in Qt 6 (QGIS 4), ``location`` in Qt 5."""
    if hasattr(QLibraryInfo, "path"):
        return QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    return QLibraryInfo.location(QLibraryInfo.LibraryLocation.TranslationsPath)


SHOTS = (("agent-settings.png", None, 712), ("agent-settings-fr.png", "fr", 766))
HEIGHT = 660
# (name, tab key of AgentSettingsDialog, what to set first, height): each one in English and in French. The height is
# the one of the page, so that the picture holds no empty half (a tab as tall as the Sources list would).
TAB_SHOTS = (("agent-sources", "sources", "sources", 660), ("agent-autonomy", "autonomy", None, 440),
             ("agent-mcp", "other_applications", "mcp", 270))
SKILL_TEXT = ("The agent wants to follow the skill \"Delivery to the town hall\" (town-hall-delivery). It comes from the "
              "folder of this project, not from FilterMate: read it before. It gives the agent no right: every change "
              "stays asked as your settings say. Let the agent use it? It is not asked again until it changes.")
SKILL_BODY = """---
name: town-hall-delivery
description: How the planning office delivers a layer to the town hall.
---
# Delivery to the town hall

When the user asks for a delivery to the town hall:

1. Name the layers with the prefix MAIRIE_ and keep the field names of the BD TOPO.
2. Use only the sources ticked in the settings: the BD TOPO of the project and the IGN WFS.
3. Export as a GeoPackage in EPSG:2154, with the styles, in the folder "livraisons" next to the project.
4. Ask before every export. Never export a layer that is not listed above.
"""


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
        if qt_translator.load(f"qtbase_{lang}", translations_path()):
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


def translators_for(lang, repo):
    items = []
    if lang:
        translator = QTranslator()
        if not translator.load(os.path.join(repo, "i18n", f"FilterMate_{lang}.qm")):
            raise RuntimeError(f"cannot load the {lang} catalog")
        items.append(translator)
        qt_translator = QTranslator()
        if qt_translator.load(f"qtbase_{lang}", translations_path()):
            items.append(qt_translator)
        for item in items:
            QCoreApplication.installTranslator(item)
    return items


def shoot_tab(out_dir, repo, name, key, prepare, height, lang, width):
    from filter_mate.adapters.agent.settings import AgentSettings, target_of
    from filter_mate.ui.widgets.agent_panel import AgentSettingsDialog

    items = translators_for(lang, repo)
    values = AgentSettings(preset="anthropic", model="claude-haiku-5-5")
    if prepare == "mcp":  # a made-up token, only to fill the field the way a real one does
        values = AgentSettings(preset="anthropic", model="claude-haiku-5-5", mcp_enabled=True, mcp_port=17823,
                               mcp_token="fm_" + "a1b2c3d4" * 4)
    dialog = AgentSettingsDialog(values, target_of, None)
    dialog.tabs.setCurrentWidget(dialog._tab_pages[key])
    if prepare == "sources":
        ticked = 0
        root = dialog.sources_tree.invisibleRootItem()
        for row in range(root.childCount()):
            group = root.child(row)
            for i in range(group.childCount()):
                title = group.child(i).text(0).lower()
                if title in ("data.gouv.fr", "ign géoplateforme (wfs)") or title.startswith("earth search"):
                    group.child(i).setCheckState(0, Qt.CheckState.Checked)
                    ticked += 1
        print("ticked", ticked, flush=True)
    for other, page in dialog._tab_pages.items():  # the tabs ask for the height of the tallest page: not this one
        if other != key:
            page.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
    dialog.resize(width, height)
    dialog.show()
    for _ in range(5):
        QCoreApplication.processEvents()
    suffix = f"-{lang}" if lang else ""
    path = os.path.join(out_dir, f"{name}{suffix}.png")
    dialog.grab().save(path, "PNG")
    print(path, dialog.size().width(), dialog.size().height(), flush=True)
    dialog.close()
    for item in items:
        QCoreApplication.removeTranslator(item)


def shoot_skill(out_dir, repo, lang, width=720, height=340):
    from filter_mate.ui.widgets.agent_panel import ask_code

    items = translators_for(lang, repo)
    suffix = f"-{lang}" if lang else ""
    path = os.path.join(out_dir, f"agent-skill{suffix}.png")

    def grab():
        for widget in QApplication.topLevelWidgets():
            if widget.isVisible() and widget.windowTitle():
                widget.resize(width, height)
                for _ in range(5):
                    QCoreApplication.processEvents()
                widget.grab().save(path, "PNG")
                print(path, widget.size().width(), widget.size().height(), flush=True)
                widget.reject()
                return
        raise RuntimeError("no dialog to grab")

    QTimer.singleShot(700, grab)
    title = QCoreApplication.translate("FilterMate", "A skill for the agent")
    text = QCoreApplication.translate("FilterMate", SKILL_TEXT)
    ask_code(None, title, text, SKILL_BODY)
    for item in items:
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
        if os.environ.get("FM_TABS"):  # the pictures of the sub-sections of the guide that had none
            for lang, width in ((None, 712), ("fr", 766)):
                for name, key, prepare, height in TAB_SHOTS:
                    shoot_tab(out, repo, name, key, prepare, height, lang, width)
                shoot_skill(out, repo, lang)
    except Exception:
        import traceback
        traceback.print_exc()
        status = 1
    os._exit(status)
