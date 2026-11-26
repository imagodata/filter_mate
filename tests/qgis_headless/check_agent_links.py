"""Agent hyperlinks with real Qt labels and a real QGIS layer tree, offscreen.

docker run --rm -v "$PWD":/src:ro -e QT_QPA_PLATFORM=offscreen qgis/qgis:ltr \
    python3 /src/tests/qgis_headless/check_agent_links.py
"""
import os
import sys
import tempfile
import traceback
import types
from types import SimpleNamespace
from unittest.mock import patch

sys.dont_write_bytecode = True
package = types.ModuleType('filter_mate')
package.__path__ = [os.environ.get('FM_REPO', '/src')]
sys.modules['filter_mate'] = package
os.environ['FILTERMATE_LOG_DIR'] = tempfile.mkdtemp(prefix='fm-links-check-logs-')

from qgis.core import QgsApplication, QgsLayerTreeModel, QgsProject, QgsVectorLayer
from qgis.gui import QgsLayerTreeView
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDockWidget, QMainWindow, QPushButton
from qgis.PyQt.QtGui import QDesktopServices
import qgis.utils

app = QgsApplication([], False)
app.initQgis()


def check(label, condition):
    assert condition, label
    print('PASS ' + label, flush=True)


def main():
    from filter_mate.ui.controllers.agent_chat_controller import AgentChatController
    from filter_mate.ui.widgets.agent_panel import AgentPanel
    from filter_mate.ui.widgets.agent_markdown import LayerReference, layer_href

    project = QgsProject.instance()
    root = project.layerTreeRoot()
    layer = QgsVectorLayer('Point?crs=EPSG:4326', 'Rivières', 'memory')
    project.addMapLayer(layer, False)
    outer = root.addGroup('Données')
    inner = outer.addGroup('Hydrographie')
    node = inner.addLayer(layer)
    node.setItemVisibilityChecked(False)
    target_id = layer.id()
    other = QgsVectorLayer('Point?crs=EPSG:4326', 'Autre', 'memory')
    project.addMapLayer(other)

    window = QMainWindow()
    window.resize(700, 500)
    dock = QDockWidget('Couches', window)
    tree = QgsLayerTreeView(dock)
    model = QgsLayerTreeModel(root)
    tree.setModel(model)
    dock.setWidget(tree)
    window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
    window.show()
    app.processEvents()
    tree.setExpanded(tree.node2index(outer), False)
    tree.setExpanded(tree.node2index(inner), False)
    dock.hide()
    panel = AgentPanel()
    recorded = []
    host = SimpleNamespace(panel=panel, _record=lambda *args, **kwargs: recorded.append((args, kwargs)))
    refs = AgentChatController._linked_layers(host)
    check('layer links include their stable id and group path',
          LayerReference(target_id, 'Rivières', 'Données / Hydrographie') in refs)
    panel.thread.layer_references = lambda: refs
    panel.thread.on_layer = lambda reference: AgentChatController._on_layer_link(host, reference)
    opened = []
    panel.thread.on_web = opened.append
    panel.thread.add_text('Les RIVIÈRES et [la source](https://example.org/source?a=1&b=2).')
    panel.thread.end_answer()
    answer = next(item for item in panel.thread._items if item.kind == 'text')
    link = layer_href(target_id)
    check('answers draw underlined layer and web hyperlinks', link in answer.widget.text()
          and 'text-decoration: underline' in answer.widget.text())
    card = panel.thread.add_card('Style de Rivières', True, '', '', ('Rivières',))
    check('action cards also link their layer names', link in card._title.text())
    face = SimpleNamespace(active=None, layerTreeView=lambda: tree)
    face.setActiveLayer = lambda found: setattr(face, 'active', found)
    with patch.object(qgis.utils, 'iface', face):
        layer.setName('Cours d’eau renommés')
        answer.widget.linkActivated.emit(link)
        app.processEvents()
        check('a link still selects the same layer after a rename', face.active is layer and tree.currentLayer() is layer)
        check('the hidden Layers dock and collapsed groups are revealed', dock.isVisible()
              and tree.isExpanded(tree.node2index(outer)) and tree.isExpanded(tree.node2index(inner)))
        check('navigation keeps visibility and the map unchanged', not node.itemVisibilityChecked())
        tree.setCurrentLayer(other)
        card._title.linkActivated.emit(link)
        check('an action card navigates to its layer', tree.currentLayer() is layer)
        answer.widget.linkHovered.emit(link)
        check('hover explains the action and shows the group path', 'Hydrographie' in answer.widget.toolTip())
        answer.widget.linkActivated.emit('https://example.org/source?a=1&b=2')
        answer.widget.linkActivated.emit('file:///etc/passwd')
        answer.widget.linkActivated.emit('javascript:alert(1)')
        check('only a user click opens a web address, with no local or application schemes',
              opened == ['https://example.org/source?a=1&b=2'])
        from filter_mate.ui.controllers.agent_outputs import AgentOutputsController
        from filter_mate.ui.widgets.agent_markdown import output_href
        from pathlib import Path
        outputs = AgentOutputsController(host)
        folder = Path(tempfile.mkdtemp(prefix='fm-output-links-'))
        path = folder / 'carte été.pdf'
        path.write_bytes(b'PDF output fixture')
        outputs.show(str(path))
        panel.thread.add_text('[La carte](file://' + str(path).replace(' ', '%20') + ') et `carte été.pdf`.')
        panel.thread.end_answer()
        output_answer = next(item for item in reversed(panel.thread._items) if item.kind == 'text')
        check('generated outputs become hyperlinks in answers', output_answer.widget.text().count(output_href(str(path))) == 2)
        output_row = next(item for item in panel.thread._items if item.kind == 'output')
        opened_files = []
        with patch.object(QDesktopServices, 'openUrl', side_effect=lambda url: opened_files.append(url.toLocalFile()) or True):
            output_row.widget.findChild(QPushButton, 'pushButton_agent_output').click()
            output_row.widget.findChild(QPushButton, 'pushButton_agent_output_folder').click()
            output_answer.widget.linkActivated.emit(output_href(str(path)))
        check('output actions open the file and its actual containing directory',
              opened_files == [str(path), str(folder), str(path)])
        check('local output links survive in the local transcript', recorded[-1][0][0] == 'output'
              and recorded[-1][1]['detail'] == str(path))
        path.unlink()
        before = len(opened_files)
        with patch.object(QDesktopServices, 'openUrl', side_effect=lambda url: opened_files.append(url.toLocalFile()) or True):
            output_answer.widget.linkActivated.emit(output_href(str(path)))
        check('a missing output reports its absence without opening another file', len(opened_files) == before)
        project.removeMapLayer(target_id)
        replacement = QgsVectorLayer('Point?crs=EPSG:4326', 'Rivières', 'memory')
        project.addMapLayer(replacement)
        face.active = other
        answer.widget.linkActivated.emit(link)
        check('a deleted layer link never selects a new layer of the same name', face.active is other)

    panel.deleteLater()
    window.close()
    project.clear()
    print('All agent hyperlink checks passed', flush=True)


try:
    main()
except Exception:
    traceback.print_exc()
    os._exit(1)
os._exit(0)
