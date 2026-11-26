import json
from pathlib import Path
import shutil
import sys
from qgis.PyQt.QtCore import QCoreApplication, Qt
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
from qgis.core import QgsApplication, QgsProject, QgsPrintLayout, QgsLayoutItemPage, QgsLayoutItemPicture
app = QgsApplication([b'filtermate-composer-preflight'], True)
app.initQgis()
sys.path.insert(0, '/w/release')
from filter_mate.core.agent.charts import ChartRequest, chart_spec, page_html
from filter_mate.adapters.agent import chart_renderer
from filter_mate.adapters.public_api.charts import add_to_layout
from filter_mate.adapters.public_api.layouts import export_layout

root = Path('/w/out')
request = ChartRequest(kind='bar', title='Prévol technique D3 — données fictives', width=640, height=400)
spec = chart_spec(request, [{'label': 'A', 'value': 7}, {'label': 'B', 'value': 3}], 'light')
code = '''
const x = d3.scaleLinear().domain([0, d3.max(data, d => d.value)]).range([80, width - 30]);
const y = d3.scaleBand().domain(data.map(d => d.label)).range([60, height - 60]).padding(0.3);
svg.append('g').attr('transform', 'translate(80,0)').call(d3.axisLeft(y));
svg.append('g').attr('transform', `translate(0,${height - 60})`).call(d3.axisBottom(x).ticks(5));
svg.selectAll('rect.bar').data(data).join('rect').attr('class', 'bar')
  .attr('x', x(0)).attr('y', d => y(d.label)).attr('width', d => x(d.value) - x(0))
  .attr('height', y.bandwidth()).attr('fill', '#22577a');
svg.append('text').attr('x', 80).attr('y', 28).text('Prévol D3 : données fictives');
'''
assert chart_renderer.available()
rendered = chart_renderer.render(page_html(spec, code))
assert not rendered.errors, rendered.errors
assert rendered.svg.count('<rect') >= 3
(root / 'd3-technical.svg').write_text(rendered.svg)
assert chart_renderer.image(rendered.svg, 1.0, '#ffffff').save(str(root / 'd3-technical.png'))
chart_renderer.drop_page()

project = QgsProject.instance()
layout = QgsPrintLayout(project)
layout.initializeDefaults()
layout.setName('Prevol_D3')
layout.pageCollection().page(0).setPageSize('A3', QgsLayoutItemPage.Orientation.Landscape)
project.layoutManager().addLayout(layout)
item = add_to_layout('Prevol_D3', rendered.svg, {'kind': 'bar', 'title': 'Prévol technique'}, 400 / 640,
                     x=250, y=40, width=145)
pdf = export_layout('Prevol_D3', str(root), file_format='pdf', dpi=150)
assert (root / pdf['path']).read_bytes().startswith(b'%PDF-')
assert project.write(str(root / 'preflight.qgz'))
moved = root / 'moved'; moved.mkdir(exist_ok=True)
shutil.copy2(root / 'preflight.qgz', moved / 'preflight.qgz')
reopened = QgsProject()
assert reopened.read(str(moved / 'preflight.qgz'))
loaded = reopened.layoutManager().layoutByName('Prevol_D3')
pictures = [it for it in loaded.items() if isinstance(it, QgsLayoutItemPicture)]
assert len(pictures) == 1 and pictures[0].picturePath().startswith('base64:')
result = {'status': 'passed', 'scope': 'technical preflight with fictitious chart data; not Urumea results',
          'qt_webengine': True, 'actual_d3_code_rendered': True, 'javascript_errors': rendered.errors,
          'svg_embedded_in_layout': True, 'pdf': pdf,
          'moved_qgz_reopened_with_embedded_svg': True,
          'full_data_portability_tested': False, 'agent_ui_take_tested': False,
          'package': json.loads(Path('/w/package.json').read_text())}
(root / 'preflight.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(result, ensure_ascii=False), flush=True)
