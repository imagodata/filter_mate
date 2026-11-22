# -*- coding: utf-8 -*-
"""Start of the standalone application: QGIS libraries, the window, then the plugin as QGIS loads it.

The plugin is not changed for this: it gets an ``iface`` (``StandaloneInterface``), finds itself
in ``qgis.utils.plugins`` and writes its configuration in the profile folder, as in QGIS. That
profile is the application's own (``standalone.paths.profile_dir``): no QGIS profile of the user
is read or written.
"""

import importlib
import os
import signal
import sys
import traceback

from .. import PACKAGE, PACKAGE_DIR, paths
from .options import build_parser

ORGANIZATION = "FilterMate"
APPLICATION = "FilterMateStandalone"


def prepare_environment(options) -> str:
    """Everything that must be decided before QGIS is imported; returns the profile folder."""
    if options.offscreen:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    profile = os.path.abspath(os.path.expanduser(options.profile or os.environ.get("FILTERMATE_PROFILE") or paths.profile_dir()))
    os.makedirs(profile, exist_ok=True)
    os.environ["QGIS_CUSTOM_CONFIG_PATH"] = profile
    if not os.environ.get("FILTERMATE_LOG_DIR"):
        os.environ["FILTERMATE_LOG_DIR"] = paths.log_dir()
    try:
        os.makedirs(os.environ["FILTERMATE_LOG_DIR"], exist_ok=True)
    except OSError:
        pass
    return profile


def display_problem() -> str:
    """A sentence when no window can be opened here, "" otherwise."""
    if not sys.platform.startswith("linux") or os.environ.get("QT_QPA_PLATFORM"):
        return ""
    if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        return ""
    return ("No display here (neither DISPLAY nor WAYLAND_DISPLAY is set). Start FilterMate from a desktop session, "
            "use the Docker image to reach it from a browser, or pass --offscreen for automation.")


def choose_locale(options) -> str:
    """The language of the session: ``--lang``, the one chosen by an earlier ``--lang``, else the system's.

    Kept in a file of the application rather than in its Qt settings: the language is needed
    before the QGIS application exists, and QGIS moves the settings into its profile folder
    when it starts.
    """
    import json
    from qgis.PyQt.QtCore import QLocale
    stored = os.path.join(paths.user_data_dir(), "settings.json")
    try:
        with open(stored, encoding="utf-8") as handle:
            saved = json.load(handle)
    except (OSError, ValueError):
        saved = {}
    if options.lang:
        saved["lang"] = options.lang
        try:
            os.makedirs(os.path.dirname(stored), exist_ok=True)
            with open(stored, "w", encoding="utf-8") as handle:
                json.dump(saved, handle, indent=1)
        except OSError:
            pass  # this session gets the language all the same
    locale = str(saved.get("lang") or "") or QLocale.system().name()
    return "en_US" if not locale or locale in ("C", "POSIX") else locale


def tell_qgis_the_locale(locale: str):
    """Where the plugin (and QGIS) read the language of the interface: the profile's settings, once QGIS runs."""
    from qgis.PyQt.QtCore import QSettings
    settings = QSettings()
    settings.setValue("locale/userLocale", locale)
    settings.setValue("locale/overrideFlag", True)


def _install_translators(app, locale: str):
    """QGIS's and Qt's own strings (the source screens, the layer panel), when QGIS did not load them itself."""
    from qgis.core import QgsApplication
    from qgis.PyQt.QtCore import QLibraryInfo, QTranslator
    try:
        qt_folder = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    except AttributeError:  # Qt5
        qt_folder = QLibraryInfo.location(QLibraryInfo.TranslationsPath)
    kept = []
    for prefix, folder in (("qgis_", QgsApplication.i18nPath()), ("qtbase_", qt_folder)):
        for code in (locale, locale.split("_")[0]):
            translator = QTranslator(app)
            if translator.load(prefix + code, folder):
                app.installTranslator(translator)
                kept.append(translator)
                break
    app._fm_translators = kept


def install_own_translator(app, locale: str):
    """The catalog of FilterMate, before the window is built: the window's own strings are in it too.

    The plugin installs the same catalog when it starts, after the window exists: too late for
    the menus and the tool tips the window set up in its constructor.
    """
    from qgis.PyQt.QtCore import QTranslator
    for code in (locale, locale.split("_")[0]):
        path = os.path.join(PACKAGE_DIR, "i18n", f"FilterMate_{code}.qm")
        translator = QTranslator(app)
        if os.path.isfile(path) and translator.load(path):
            app.installTranslator(translator)
            app._fm_own_translator = translator
            return True
    return False


def init_processing() -> bool:
    """Processing, as QGIS starts it: the agent and the automation run its algorithms."""
    from qgis.core import QgsApplication
    try:
        folder = os.path.join(QgsApplication.pkgDataPath(), "python", "plugins")
        if os.path.isdir(folder) and folder not in sys.path:
            sys.path.append(folder)
        from processing.core.Processing import Processing
        Processing.initialize()
        return True
    except Exception as error:
        print(f"FilterMate: Processing is not available ({error})", file=sys.stderr)
        return False


def load_plugin(interface):
    """Load FilterMate the way QGIS loads a plugin, and open its dock."""
    import qgis.utils
    package = importlib.import_module(PACKAGE)
    plugin = package.classFactory(interface)
    qgis.utils.plugins[PACKAGE] = plugin
    for registry in (qgis.utils.active_plugins, qgis.utils.available_plugins):
        if PACKAGE not in registry:
            registry.append(PACKAGE)
    plugin.initGui()
    plugin.run()
    return plugin


def unload_plugin():
    import qgis.utils
    plugin = qgis.utils.plugins.pop(PACKAGE, None)
    if plugin is None:
        return
    try:
        plugin.unload()
    except Exception:
        traceback.print_exc()
    if PACKAGE in qgis.utils.active_plugins:
        qgis.utils.active_plugins.remove(PACKAGE)


def _install_excepthook(window):
    """An error in a handler is shown and logged, and the application goes on (Qt would abort it)."""
    from qgis.core import Qgis, QgsMessageLog

    def hook(kind, value, trace):
        text = "".join(traceback.format_exception(kind, value, trace))
        sys.stderr.write(text)
        sys.stderr.flush()
        try:
            QgsMessageLog.logMessage(text, "Python", Qgis.MessageLevel.Critical)
            window.message_bar.pushCritical("FilterMate", f"{kind.__name__}: {value}")
        except Exception:  # nosec B110 - the error is already on stderr
            pass

    sys.excepthook = hook


def _run_code(path: str, app) -> None:
    """Run a Python file in the application, as ``qgis --code`` does."""
    import runpy
    try:
        runpy.run_path(os.path.abspath(path), run_name="__main__")
    except SystemExit as stop:
        code = stop.code if isinstance(stop.code, int) else (0 if stop.code is None else 1)
        app.exit(code)
    except Exception:
        traceback.print_exc()
        app.exit(1)


def _parse_size(text):
    try:
        width, height = (int(part) for part in str(text).lower().split("x", 1))
        return (width, height) if width >= 320 and height >= 240 else None
    except (TypeError, ValueError):
        return None


def main(argv=None) -> int:
    options = build_parser().parse_args(list(sys.argv[1:] if argv is None else argv))
    problem = "" if options.offscreen else display_problem()
    if problem:
        print(f"FilterMate: {problem}", file=sys.stderr)
        return 2
    profile = prepare_environment(options)
    automated = bool(options.code)

    from qgis.core import QgsApplication
    from qgis.PyQt.QtCore import QT_VERSION_STR, QCoreApplication, QLocale, QSettings, Qt, QTimer
    from qgis.PyQt.QtGui import QIcon

    # The settings of the application live in its profile folder, not in the registry or ~/.config.
    QCoreApplication.setOrganizationName(ORGANIZATION)
    QCoreApplication.setOrganizationDomain("filtermate.app")
    QCoreApplication.setApplicationName(APPLICATION)
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, profile)

    locale = choose_locale(options)
    QLocale.setDefault(QLocale(locale))
    translated_by_qgis = hasattr(QgsApplication, "setTranslation")
    if translated_by_qgis:
        QgsApplication.setTranslation(locale)
    if QT_VERSION_STR.startswith("5."):  # always on in Qt6, where setting them only warns
        for attribute in ("AA_EnableHighDpiScaling", "AA_UseHighDpiPixmaps"):
            flag = getattr(Qt.ApplicationAttribute, attribute, None)
            if flag is not None:
                QCoreApplication.setAttribute(flag, True)
    if os.environ.get("QGIS_PREFIX_PATH"):
        QgsApplication.setPrefixPath(os.environ["QGIS_PREFIX_PATH"], True)

    app = QgsApplication([], True)
    app.setWindowIcon(QIcon(os.path.join(PACKAGE_DIR, "icon.png")))
    if hasattr(app, "setDesktopFileName"):
        app.setDesktopFileName("filtermate")
    app.initQgis()
    if not translated_by_qgis:
        _install_translators(app, locale)
    tell_qgis_the_locale(locale)
    install_own_translator(app, locale)
    signal.signal(signal.SIGINT, signal.SIG_DFL)  # Ctrl+C in the terminal stops the application

    import qgis.utils

    from .interface import StandaloneInterface
    from .window import StandaloneWindow

    window = StandaloneWindow(interactive=not automated)
    interface = StandaloneInterface(window)
    window.interface = interface
    qgis.utils.iface = interface  # before any module of the plugin is imported: they bind it at import
    _install_excepthook(window)

    window.restore_window()
    size = _parse_size(options.size)
    if size:
        window.resize(*size)
    if options.maximized:
        window.showMaximized()
    else:
        window.show()
    app.processEvents()
    init_processing()

    welcome_keys = ("FilterMate/discord_welcome_dismissed", "FilterMate/whats_new_seen")
    kept_welcome = {}
    if automated or options.no_welcome:
        # For this session only: the values a user would see next time are put back when it ends.
        settings = QSettings()
        kept_welcome = {key: settings.value(key) for key in welcome_keys}
        settings.setValue("FilterMate/discord_welcome_dismissed", True)
        settings.setValue("FilterMate/whats_new_seen", 9999)

    def restore_welcome():
        settings = QSettings()
        for key, value in kept_welcome.items():
            if value is None:
                settings.remove(key)
            else:
                settings.setValue(key, value)

    state = {"plugin": None}

    def closing():
        unload_plugin()
        state["plugin"] = None
        restore_welcome()

    window.closing = closing

    def start():
        if not options.no_plugin:
            try:
                state["plugin"] = load_plugin(interface)
            except Exception as error:
                traceback.print_exc()
                window.message_bar.pushCritical("FilterMate", f"FilterMate could not start: {error}")
                if automated:
                    app.exit(1)
                    return
        if options.project:
            window.open_project(options.project)
        if options.paths:
            window.sources.open_paths(options.paths)
        if options.basemap:
            window.sources.add_basemap()
        interface.initializationCompleted.emit()
        if options.code:
            _run_code(options.code, app)

    QTimer.singleShot(0, start)
    code = app.exec()

    if state["plugin"] is not None:  # the loop ended without the window closing (app.exit from a script)
        closing()
    window.disconnect_project()
    restore_welcome()
    try:
        from qgis.core import QgsProject
        QgsProject.instance().clear()
    except Exception:  # nosec B110 - leaving anyway
        pass
    finish(app, int(code or 0))


def finish(app, code: int):
    """Leave without the crash of Python's own end: never returns.

    Left to the interpreter, the end of Python destroys the widgets it still holds after the
    application object is gone, and the process dies in ``QWidget::~QWidget`` (seen on most
    runs under a real display, QGIS 3.22, 3.44 and 4.3: exit codes 134 and 139). Deleting the
    windows first is no better: Qt then dies in the deferred deletions, one run in four. So
    nothing is destroyed: the windows are hidden, what Python runs at exit (``atexit``: the
    database pools and the caches of the plugin) runs while QGIS still runs, as in QGIS, the
    settings and the logs are written, QGIS is closed, and the process ends there with the application's exit code. The system
    takes the memory back, as it does for any process.
    """
    import atexit
    import logging

    from qgis.PyQt.QtCore import QSettings
    try:
        for widget in app.topLevelWidgets():
            widget.hide()
    except Exception:  # nosec B110 - leaving anyway
        traceback.print_exc()
    # The order of QGIS: Python's own end (the atexit handlers of the plugin) while QGIS still runs, then QGIS.
    try:
        atexit._run_exitfuncs()
    except Exception:  # nosec B110 - leaving anyway
        traceback.print_exc()
    try:
        QSettings().sync()
    except Exception:  # nosec B110 - leaving anyway
        traceback.print_exc()
    logging.shutdown()
    try:
        app.exitQgis()
    except Exception:  # nosec B110 - leaving anyway
        traceback.print_exc()
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except Exception:  # nosec B110 - a closed stream has nothing left to write
            pass
    os._exit(code)


if __name__ == "__main__":
    sys.exit(main())
