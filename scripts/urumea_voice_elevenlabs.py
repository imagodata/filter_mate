#!/usr/bin/env python3
"""Generate Urumea French narration with ElevenLabs; keep credentials local.

Reads ELEVENLABS_API_KEY from the environment or --env-file. Completed matching
requests are reused using both request and audio hashes. No automatic retries
are made for generation requests. --dry-run never reads the key or uses network.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import urllib.error
import urllib.request


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def api_key(env_file):
    value = os.environ.get('ELEVENLABS_API_KEY')
    if value:
        return value
    if env_file.is_file():
        for line in env_file.read_text(encoding='utf-8').splitlines():
            name, separator, value = line.partition('=')
            if separator and name.strip().removeprefix('export ').strip() == 'ELEVENLABS_API_KEY':
                words = shlex.split(value, comments=True)
                if len(words) == 1 and words[0]:
                    return words[0]
    raise RuntimeError('Configure ELEVENLABS_API_KEY locally; do not paste it in chat')


def audio_info(path, ffprobe):
    info = json.loads(subprocess.check_output([
        ffprobe, '-v', 'error', '-show_entries',
        'format=duration:stream=codec_type,codec_name,sample_rate,channels',
        '-of', 'json', str(path)], text=True))
    audio = [stream for stream in info['streams'] if stream['codec_type'] == 'audio']
    if len(audio) != 1 or float(info['format']['duration']) <= 0:
        raise RuntimeError('Expected one nonempty audio stream')
    return {'duration_s': float(info['format']['duration']), **audio[0]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--env-file', type=Path, default=Path('.env'))
    parser.add_argument('--ffprobe', default='ffprobe')
    parser.add_argument('--only', action='append', default=[])
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--force', action='store_true', help='Regenerate existing nonmatching output')
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding='utf-8'))
    ids = [line['id'] for line in spec['lines']]
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', name) for name in ids):
        parser.error('Narration ids must be unique and filename-safe')
    if set(args.only) - set(ids):
        parser.error('Unknown --only id')
    if not re.fullmatch(r'[A-Za-z0-9]+', spec['voice_id']):
        parser.error('Invalid voice_id')
    lines = [line for line in spec['lines'] if not args.only or line['id'] in args.only]
    if not lines or any(not line['text'].strip() for line in lines):
        parser.error('Expected nonempty narration')
    args.output.mkdir(parents=True, exist_ok=True)
    plan = []
    for line in lines:
        payload = {
            'text': line.get('tts_text', spec.get('direction', '') + line['text']),
            'model_id': spec['model_id'],
            'language_code': spec.get('language_code', 'fr'),
            'voice_settings': spec.get('voice_settings', {}),
        }
        request = {'voice_id': spec['voice_id'], 'output_format': 'mp3_44100_128', 'payload': payload}
        fingerprint = hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        plan.append({'id': line['id'], 'text': line['text'], 'request': request, 'request_sha256': fingerprint})
    write_json(args.output / 'request-plan.json', {'provider': 'elevenlabs', 'requests': plan})
    if args.dry_run:
        print(f'Prepared {len(plan)} requests; no network call made')
        return
    # Resolve the key and ffprobe before any synthesis request consumes credits.
    key = api_key(args.env_file)
    subprocess.run([args.ffprobe, '-version'], check=True, stdout=subprocess.DEVNULL)
    manifest_path = args.output / 'voice-manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {
        'provider': 'elevenlabs', 'voice_name': spec['voice_name'], 'voice_id': spec['voice_id'],
        'model_id': spec['model_id'], 'publication': 'not_published', 'lines': []}
    completed = {entry['id']: entry for entry in manifest['lines']}
    for item in plan:
        path = args.output / (item['id'] + '.mp3')
        old = completed.get(item['id'], {})
        if path.is_file() and old.get('request_sha256') == item['request_sha256'] and old.get('sha256') == hashlib.sha256(path.read_bytes()).hexdigest():
            audio_info(path, args.ffprobe)
            print(f"{item['id']}: reused verified audio", flush=True)
            continue
        if path.exists() and not args.force:
            raise RuntimeError(f'{path.name}: existing output differs; use another folder or --force')
        request = urllib.request.Request(
            'https://api.elevenlabs.io/v1/text-to-speech/' + spec['voice_id'] + '?output_format=mp3_44100_128',
            data=json.dumps(item['request']['payload'], ensure_ascii=False).encode(),
            headers={'xi-api-key': key, 'Content-Type': 'application/json', 'Accept': 'audio/mpeg'},
            method='POST')
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                content_type = response.headers.get('Content-Type', '')
                audio = response.read()
        except urllib.error.HTTPError as error:
            try:
                detail = json.load(error).get('detail', {})
                status = detail.get('status', 'unknown') if isinstance(detail, dict) else 'unknown'
            except (ValueError, AttributeError):
                status = 'unknown'
            status = re.sub(r'[^A-Za-z0-9_.-]', '', str(status))[:80]
            raise RuntimeError(f'ElevenLabs HTTP {error.code}: {status}; request not retried') from None
        if not content_type.startswith('audio/') or len(audio) < 1000:
            raise RuntimeError('ElevenLabs did not return nonempty audio; request not retried')
        temporary = path.with_suffix('.pending.mp3')
        temporary.write_bytes(audio)
        measured = audio_info(temporary, args.ffprobe)
        temporary.replace(path)
        completed[item['id']] = {
            'id': item['id'], 'text': item['text'], 'file': path.name,
            'request_sha256': item['request_sha256'],
            'sha256': hashlib.sha256(audio).hexdigest(), **measured}
        manifest['lines'] = list(completed.values())
        write_json(manifest_path, manifest)
        print(f"{item['id']}: {measured['duration_s']:.2f} s", flush=True)


if __name__ == '__main__':
    main()
