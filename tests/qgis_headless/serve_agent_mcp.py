# -*- coding: utf-8 -*-
"""A QGIS with the MCP server of FilterMate on, for a real MCP client to talk to (tests/mcp_client_check.py).

    docker run --rm --network host -e FM_MCP_PORT=17899 -e FM_MCP_TOKEN=... -v "$PWD:/src:ro" qgis/qgis:ltr ...

Serves for FM_SERVE_SECONDS (default 120), then exits. No model and no network beyond the loopback.
"""
import os
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HOME = tempfile.mkdtemp()
os.environ["QGIS_CUSTOM_CONFIG_PATH"] = HOME
os.environ["QGIS_AUTH_DB_DIR_PATH"] = HOME

from qgis.core import QgsApplication, QgsFeature, QgsGeometry, QgsPointXY, QgsProject, QgsVectorFileWriter, QgsVectorLayer  # noqa: E402
from qgis.PyQt.QtCore import QCoreApplication  # noqa: E402
from qgis.PyQt.QtWidgets import QLabel, QToolBox  # noqa: E402


def _link(source, target):
    """A link to the plugin folder: a symlink, or a junction on Windows (no privilege needed)."""
    try:
        os.symlink(source, target)
    except OSError:
        if os.name != "nt":
            raise
        import subprocess
        subprocess.run(["cmd", "/c", "mklink", "/J", target, source], check=True, capture_output=True)


def make_layer(path):
    memory = QgsVectorLayer("Point?crs=EPSG:2154&field=pop:integer", "m", "memory")
    features = []
    for index in range(1, 61):
        feature = QgsFeature(memory.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(650000 + index, 6860000)))
        feature.setAttributes([index * 100])
        features.append(feature)
    memory.dataProvider().addFeatures(features)
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    QgsVectorFileWriter.writeAsVectorFormatV3(memory, path, QgsProject.instance().transformContext(), options)
    return QgsVectorLayer(path, "communes", "ogr")


def main():
    from filter_mate.adapters.agent.settings import AgentSettings, save_settings
    from filter_mate.adapters.public_api.filter_mate_public_api import FilterMatePublicAPI
    from filter_mate.ui.controllers.agent_chat_controller import AgentChatController

    layer = make_layer(os.path.join(tempfile.mkdtemp(), "communes.gpkg"))
    QgsProject.instance().addMapLayer(layer)
    api = FilterMatePublicAPI(None)

    class Plugin:
        def get_public_api(self):
            return api

    save_settings(AgentSettings(mcp_enabled=True, mcp_port=int(os.environ["FM_MCP_PORT"]), mcp_token=os.environ["FM_MCP_TOKEN"]))
    host = QToolBox()
    host.addItem(QLabel("filtering"), "FILTERING")
    chat = AgentChatController(lambda page: host.insertItem(0, page, "AGENT"), Plugin(), host,
                               ask_user=lambda title, text: os.environ.get("FM_ANSWER", "no") == "yes")
    print(f"listening={chat._mcp.listening} error={chat._mcp.error!r}", flush=True)
    deadline = time.time() + float(os.environ.get("FM_SERVE_SECONDS", "120"))
    last = None
    while time.time() < deadline:
        QCoreApplication.processEvents()
        if layer.subsetString() != last:
            last = layer.subsetString()
            print(f"subset={last!r}", flush=True)
        time.sleep(0.005)
    print("thread:", chat.panel.thread.toPlainText().replace("\n", " | ")[-600:], flush=True)
    chat.shutdown()


if __name__ == "__main__":
    app = QgsApplication([], True)
    app.initQgis()
    package_root = tempfile.mkdtemp()
    _link(os.environ.get("FM_REPO", "/src"), os.path.join(package_root, "filter_mate"))
    sys.path.insert(0, package_root)
    sys.dont_write_bytecode = True
    main()
    os._exit(0)
