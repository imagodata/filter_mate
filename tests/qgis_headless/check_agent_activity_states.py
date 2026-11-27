"""Real QtSvg rendering of every task and user state, with static completion and visible-only animation."""
import json
import os
import sys
import types
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from qgis.core import QgsApplication, Qgis
from qgis.PyQt.QtCore import QByteArray, QEventLoop, QTimer, Qt
from qgis.PyQt.QtGui import QImage, QPainter
from qgis.PyQt.QtSvg import QSvgRenderer
from qgis.PyQt.QtWidgets import QWidget

app = QgsApplication([], False)
app.initQgis()
root = Path(os.environ.get('FM_REPO', '/src'))
package = types.ModuleType('filter_mate')
package.__path__ = [str(root)]
sys.modules['filter_mate'] = package
from filter_mate.ui.widgets.agent_activity import AgentActivityIcon
from filter_mate.ui.styles.mockup_design import AGENT_ACTIVITY_STYLES, STATIC_AGENT_PHASES, agent_activity_svg, tokens


def wait(ms=200):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


parent = QWidget()
widget = AgentActivityIcon(parent)
parent.show()
app.processEvents()
assert widget.isVisible() and widget.display_phase == 'idle' and not widget._renderer.animated()
for dark in (False, True):
    widget.refresh_look(dark)
    pictures = []
    for phase in AGENT_ACTIVITY_STYLES:
        renderer = QSvgRenderer(QByteArray(agent_activity_svg(tokens(dark)['fm_icon'], False, phase).encode()))
        assert renderer.isValid() and not renderer.animated(), phase
        picture = QImage(64, 64, QImage.Format.Format_ARGB32)
        picture.fill(Qt.GlobalColor.transparent)
        painter = QPainter(picture)
        renderer.render(painter)
        painter.end()
        assert all(picture != previous for previous in pictures), phase
        pictures.append(picture)
        widget.set_working(True)
        widget.set_phase(phase)
        assert widget._renderer.animated() == (phase not in STATIC_AGENT_PHASES), phase
    print(f'PASS {len(pictures)} distinct valid states, theme {"dark" if dark else "light"}', flush=True)

for phase in ('processing', 'searching', 'exporting', 'confirming'):
    widget.set_phase(phase)
    before = widget.grab().toImage()
    changed = False
    for _ in range(5):  # the calm 3.8 s pulse needs more time than the fast orbital states at 32 px
        wait(250)
        if widget.grab().toImage() != before:
            changed = True
            break
    assert changed, phase
widget.set_working(False)
assert widget.display_phase == 'complete' and widget.isVisible() and not widget._renderer.animated()
before = widget.grab().toImage()
wait()
assert widget.grab().toImage() == before
widget.set_interaction('drafting')
assert not widget._renderer.animated() and widget.display_phase == 'drafting'
widget.set_interaction('listening')
assert widget._renderer.animated() and widget.display_phase == 'listening'
parent.hide()
assert not widget._renderer.animated()
parent.show()
assert widget._renderer.animated()
widget.set_interaction('')
assert widget.display_phase == 'complete' and not widget._renderer.animated()
print('PASS task motion, persistent static completion, typing, voice and visibility lifetime', flush=True)

board = QSvgRenderer(str(root / 'docs/design/agent-identity/agent-states-static.svg'))
assert board.isValid() and not board.animated()
picture = QImage(board.defaultSize(), QImage.Format.Format_ARGB32)
picture.fill(Qt.GlobalColor.transparent)
painter = QPainter(picture)
board.render(painter)
painter.end()
out = Path(os.environ.get('FM_ACTIVITY_OUTPUT', '/audit/fm-agent-states'))
assert picture.save(str(out.with_suffix('.png')))
out.with_suffix('.json').write_text(json.dumps({'qgis': Qgis.QGIS_VERSION, 'states': len(AGENT_ACTIVITY_STYLES),
                                              'static_states': sorted(STATIC_AGENT_PHASES), 'passed': True}, indent=2))
print(f'PASS QGIS {Qgis.QGIS_VERSION}: review board rendered', flush=True)
os._exit(0)
