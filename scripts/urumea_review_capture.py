"""Record the moved project, native fitted composer and actual PDF offline.

These are review shots of the deliverables, never substitutes for the footage
of the agent actually creating charts, layouts and exports.
"""
from pathlib import Path
exec(compile(Path('/w/scripts/urumea_full_capture.py').read_text(),
             '/w/scripts/urumea_full_capture.py', 'exec'), globals())


def review_map():
    presentation('final')
    REC.event('mark', name='moved-project-opened')


def review_composer():
    layout = QgsProject.instance().layoutManager().layoutByName('Urumea — analyse')
    if layout is None:
        raise RuntimeError('Missing delivered layout')
    designer = iface.openLayoutDesigner(layout)
    designer.window().setGeometry(315, 145, 1115, 800)
    QTimer.singleShot(500, designer.view().zoomFull)
    QTimer.singleShot(1500, designer.view().zoomFull)
    REC.event('mark', name='moved-composer-opened')


STEPS = [(1000, setup_visible), (3000, open_plugin), (6000, size_dock), (1000, wait_idle()),
         (600, configure_agent), (400, agent_open), (600, align_dock), (800, wait_idle()),
         (0, review_map), (500, rec_start), hold(5500), still('moved-project'),
         (0, review_composer), hold(6000), still('composer-fit'), hold(2500),
         (0, close_composer), (1000, open_pdf), hold(6500), still('pdf-fit'),
         (0, close_pdf), hold(2000), (0, stop_recording), (500, quit_when_idle)]
log('Review shots: moved project opened offline; native composition and PDF')
