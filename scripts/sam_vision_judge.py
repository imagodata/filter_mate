"""Can a model looking at a contact sheet sort the similar objects SAM proposes? (the trial of the MCP images)

Pre-registered 2026-11-11, before any call to a model:

- The proposals are those of the search of the dock adopted on 2026-11-11 (colour patches, then the 10 best feature
  peaks, appearance at least 0.68), replayed from the output of scripts/sam_similar_candidates.py on the 20 buildings
  of the 25 cm Cerdagne orthophoto (sets A and B as there). A proposal is right when it matches a BD TOPO building
  at IoU >= 0.5.
- Each search becomes one contact sheet made by adapters/public_api/map_images.sheet_image, the code of the
  contact_sheet tool of the MCP server: tile E the clicked object, then the first 30 proposals, tiles of 160 pixels.
- Model: claude-haiku-5-5, one request per sheet, the PROMPT below, nothing else; no setting is chosen. (Written
  "temperature 0" first; the API refuses temperature for this model, so its default is used: changed after the
  first request failed, before any answer was read. Then max_tokens 300: the model spent them reasoning and 16 of
  the 20 answers were empty, no judgement at all; raised to 4000 and every sheet asked again, the prompt, the model
  and the rule unchanged.)
- Adopted as the way to sort proposals with an MCP client if, on set B, the median precision of the proposals the
  model keeps gains at least 0.10 over the median precision of all the proposals shown, and the median recall (truth
  buildings matched by the proposals kept, over those matched by the proposals shown) is at least 0.95. Set A is
  reported too.

Three steps (the second in QGIS for Windows, by python-qgis.bat):

    uvx --with shapely --with numpy python scripts/sam_vision_judge.py prepare candidates.json proposals.json
    python-qgis.bat scripts/sam_vision_judge.py render <plugins folder> <ortho> proposals.json <sheets folder>
    python3 scripts/sam_vision_judge.py judge proposals.json <sheets folder> <key file> results.json
"""
import base64
import json
import os
import re
import statistics
import sys
import time

MODEL = "claude-haiku-5-5"
MAX_TILES = 30
TILE = 160
PROMPT = (
    "This contact sheet shows tiles cut out of an aerial orthophoto (about 25 cm per pixel). Tile E shows an example "
    "object, outlined in red. Tiles 1 to {count} each show a candidate object, outlined in red. Which candidates are "
    "the same kind of object as the example, judged by what the object is and not only by its colour? Answer only "
    "with JSON: {{\"alike\": [the tile numbers]}}.")


def prepare(candidates_path: str, output: str) -> None:
    """Replay the adopted search on every reference; write the clicked object and its proposals, with the truth."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import sam_similar_candidates_analysis as analysis
    rows = analysis.load(candidates_path)
    searches = []
    for row in rows:
        if row['_clicked'] is None:
            continue
        prompts = analysis.colour_prompts(row) + analysis.feature_prompts(row, 0.3, 10)
        proposals, _drawn = analysis.replay(row, prompts, analysis.BASELINE_APPEARANCE)
        shown = proposals[:MAX_TILES]
        analysis.measure(row, shown)  # fills _match
        searches.append({'fid': row['fid'], 'set': row['set'], 'clicked': row['clicked'], 'truth': row['truth'],
                         'proposals': [{'wkt': c['wkt'], 'match': c['_match']} for c in shown],
                         'left_out': max(0, len(proposals) - MAX_TILES)})
    with open(output, 'w', encoding='utf-8') as stream:
        json.dump(searches, stream)
    print(f"{len(searches)} searches, {sum(len(s['proposals']) for s in searches)} proposals shown")


def render(plugins: str, ortho: str, proposals_path: str, folder: str) -> None:
    """One contact sheet per search, by the code of the contact_sheet tool (QGIS, offscreen)."""
    sys.path.insert(0, plugins)
    if os.name != 'nt':  # the offscreen platform of Qt for Windows has no fonts: the tile numbers would be boxes
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from qgis.core import QgsApplication, QgsGeometry, QgsRasterLayer
    app = QgsApplication([], True)
    app.initQgis()
    from filter_mate.adapters.public_api import map_images
    layer = QgsRasterLayer(ortho, 'ortho', 'gdal')
    assert layer.isValid()
    os.makedirs(folder, exist_ok=True)
    for search in json.load(open(proposals_path, encoding='utf-8')):
        if not search['proposals']:
            continue
        sheet = map_images.sheet_image(layer, QgsGeometry.fromWkt(search['clicked']),
                                       [QgsGeometry.fromWkt(p['wkt']) for p in search['proposals']], TILE)
        path = os.path.join(folder, f"sheet_{search['fid']}.jpg")
        assert sheet.save(path, 'JPEG', map_images.JPEG_QUALITY), path
        print(path, flush=True)
    print('done', flush=True)
    os._exit(0)


def ask(key: str, image_path: str, count: int) -> dict:
    """One request to the Messages API; the text of the answer and the tokens used."""
    import urllib.request
    data = base64.b64encode(open(image_path, 'rb').read()).decode('ascii')
    body = {'model': MODEL, 'max_tokens': 4000, 'messages': [{'role': 'user', 'content': [
        {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': data}},
        {'type': 'text', 'text': PROMPT.format(count=count)}]}]}
    request = urllib.request.Request('https://api.anthropic.com/v1/messages', data=json.dumps(body).encode('utf-8'),
                                     headers={'x-api-key': key, 'anthropic-version': '2023-06-01',
                                              'content-type': 'application/json', 'user-agent': 'FilterMate-bench'},
                                     method='POST')
    import urllib.error
    try:
        with urllib.request.urlopen(request, timeout=120) as response:  # nosec B310 - a fixed https URL
            answer = json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:500]}") from None
    text = ''.join(block.get('text', '') for block in answer.get('content', []) if block.get('type') == 'text')
    return {'text': text, 'usage': answer.get('usage', {})}


def kept_tiles(text: str, count: int) -> list:
    match = re.search(r'\{.*\}', text, re.S)
    try:
        values = json.loads(match.group(0)).get('alike', []) if match else []
    except ValueError:
        values = []
    return sorted({int(v) for v in values if isinstance(v, (int, float)) and 1 <= int(v) <= count})


def metrics(search: dict, kept: list) -> tuple:
    proposals = search['proposals']
    chosen = [proposals[tile - 1] for tile in kept]
    precision_all = sum(1 for p in proposals if p['match']) / len(proposals)
    precision_kept = (sum(1 for p in chosen if p['match']) / len(chosen)) if chosen else None
    truth = set(search['truth'])
    reachable = {i for p in proposals for i in p['match'] if i in truth}
    kept_truth = {i for p in chosen for i in p['match'] if i in truth}
    recall = len(kept_truth) / len(reachable) if reachable else None
    return precision_all, precision_kept, recall


def judge(proposals_path: str, folder: str, key_file: str, output: str) -> None:
    key = open(os.path.expanduser(key_file), encoding='utf-8').read().strip()
    results = []
    for search in json.load(open(proposals_path, encoding='utf-8')):
        path = os.path.join(folder, f"sheet_{search['fid']}.jpg")
        if not search['proposals'] or not os.path.exists(path):
            continue
        count = len(search['proposals'])
        answer = ask(key, path, count)
        kept = kept_tiles(answer['text'], count)
        precision_all, precision_kept, recall = metrics(search, kept)
        results.append({'fid': search['fid'], 'set': search['set'], 'shown': count, 'kept': kept,
                        'precision_all': precision_all, 'precision_kept': precision_kept, 'recall': recall,
                        'answer': answer['text'][:500], 'usage': answer['usage']})
        print(json.dumps({k: results[-1][k] for k in ('fid', 'set', 'shown', 'kept', 'precision_all',
                                                      'precision_kept', 'recall')}), flush=True)
        time.sleep(1)
    with open(output, 'w', encoding='utf-8') as stream:
        json.dump(results, stream, indent=1)
    for name in ('A', 'B'):
        rows = [r for r in results if r['set'] == name]
        if not rows:
            continue
        median = lambda values: round(statistics.median(values), 3) if values else 0.0  # noqa: E731
        p_all = median([r['precision_all'] for r in rows])
        p_kept = median([r['precision_kept'] for r in rows if r['precision_kept'] is not None])
        recall = median([r['recall'] for r in rows if r['recall'] is not None])
        print(f"set {name}: precision of all shown {p_all}, of those kept {p_kept}, recall of the reachable {recall} "
              f"({len(rows)} sheets, {sum(1 for r in rows if not r['kept'])} with nothing kept)")
        if name == 'B':
            adopted = p_kept >= p_all + 0.10 and recall >= 0.95
            print('  ADOPTED' if adopted else '  not adopted')
    tokens = {key: sum(r['usage'].get(key, 0) for r in results) for key in ('input_tokens', 'output_tokens')}
    print(f"tokens: {tokens}")


if __name__ == '__main__':
    command, arguments = sys.argv[1], sys.argv[2:]
    {'prepare': prepare, 'render': render, 'judge': judge}[command](*arguments)
