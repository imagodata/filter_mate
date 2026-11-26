#!/usr/bin/env python3
"""Generate local French narration with Kokoro ONNX, without an online API.

Requires kokoro-onnx and soundfile in a dedicated Python environment. Download
the model and voices from the upstream release; do not add them to the plugin.
See docs/communication/lot5/urumea-slope-proposal/README.md.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', type=Path, required=True)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--voices', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding='utf-8'))
    lines = spec['lines']
    ids = [line['id'] for line in lines]
    if len(set(ids)) != len(ids) or any(
            not identifier or Path(identifier).name != identifier
            or identifier in ('.', '..') for identifier in ids):
        parser.error('Each line needs a unique filename-safe id')
    if any(not line['text'].strip() for line in lines):
        parser.error('Narration text must not be empty')

    import soundfile as sf
    from kokoro_onnx import Kokoro
    model = Kokoro(str(args.model), str(args.voices))
    args.output.mkdir(parents=True, exist_ok=True)
    settings = {
        'voice': spec.get('voice', 'ff_siwis'),
        'speed': spec.get('speed', 0.88),
        'lang': spec.get('language', 'fr-fr'),
        'sentence_pause': spec.get('sentence_pause', 0.55),
        'clause_pause': spec.get('clause_pause', 0.15),
    }
    manifest = {
        'engine': 'kokoro-onnx',
        'engine_version': importlib.metadata.version('kokoro-onnx'),
        'model_sha256': digest(args.model),
        'voices_sha256': digest(args.voices),
        'spec_sha256': digest(args.spec),
        'settings': settings,
        'status': 'audition_only_not_final_video',
        'lines': [],
    }
    for line in lines:
        samples, sample_rate = model.create(line['text'], **settings)
        path = args.output / (line['id'] + '.wav')
        sf.write(path, samples, sample_rate, subtype='PCM_16')
        entry = {
            'id': line['id'], 'text': line['text'], 'file': path.name,
            'duration_s': len(samples) / sample_rate,
            'sample_rate': sample_rate, 'channels': 1,
            'sha256': digest(path),
        }
        manifest['lines'].append(entry)
        print(f"{line['id']}: {entry['duration_s']:.2f} s", flush=True)
    (args.output / 'voice-manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8')


if __name__ == '__main__':
    main()
