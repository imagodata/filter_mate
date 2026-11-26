# -*- coding: utf-8 -*-
"""Voice-over of the Sarlat LinkedIn clips (``scripts/sarlat_narration.json``), run from WSL.

Usage::

    python3 scripts/fm5_clip_voice.py <fm_video folder> <ffprobe.exe or ffprobe> [clip ...]

Languages from ``FM_LANGS`` (default ``en``). Engine from ``FM_VOICE_ENGINE``: ``edge-tts`` (default, ``pip install edge-tts``) or ``elevenlabs``
(``ELEVENLABS_API_KEY`` in the environment; ``FM_ELEVEN_VOICE_FR`` / ``FM_ELEVEN_VOICE_EN`` are voice ids,
``FM_ELEVEN_MODEL`` the model, default ``eleven_multilingual_v2``). Writes, per engine and language,
``<fm_video>/voice/<engine>/<lang>/<clip>-<line>.mp3`` and ``<fm_video>/scripts/narration_durations.json``
(longest of the languages, per clip and line): the recording waits that long after each line so
that both voice-overs fit the same picture.
"""
import json
import os
import argparse
import subprocess
import sys

import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


def duration(ffprobe, path):
    if ffprobe.lower().endswith('.exe') and sys.platform != 'win32':
        path = subprocess.run(['wslpath', '-w', path], capture_output=True, text=True, check=True).stdout.strip()
    out = subprocess.run([ffprobe, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


ENGINE = os.environ.get('FM_VOICE_ENGINE', 'edge-tts')
LANGS = os.environ.get('FM_LANGS', 'en').split(',')
# premade ElevenLabs voices that speak French and English with the multilingual model
ELEVEN_VOICES = {'fr': os.environ.get('FM_ELEVEN_VOICE_FR', 'onwK4e9ZLuTAKqWW03F9'),   # Daniel
                 'en': os.environ.get('FM_ELEVEN_VOICE_EN', 'onwK4e9ZLuTAKqWW03F9')}


def speak_edge(text, voice, path):
    import asyncio
    import edge_tts
    asyncio.run(edge_tts.Communicate(text, voice, rate='-4%').save(path))


def speak_eleven(text, lang, path):
    request = urllib.request.Request(
        f'https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICES[lang]}?output_format=mp3_44100_128',
        data=json.dumps({'text': text, 'model_id': os.environ.get('FM_ELEVEN_MODEL', 'eleven_multilingual_v2'),
                         'language_code': lang,
                         'voice_settings': {'stability': 0.5, 'similarity_boost': 0.75, 'style': 0.15}}).encode(),
        headers={'xi-api-key': os.environ['ELEVENLABS_API_KEY'], 'Content-Type': 'application/json',
                 'Accept': 'audio/mpeg'})
    with urllib.request.urlopen(request, timeout=120) as response, open(path, 'wb') as out:
        out.write(response.read())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root')
    parser.add_argument('ffprobe')
    parser.add_argument('clips', nargs='*')
    parser.add_argument('--durations-only', action='store_true', help='inspect existing audio, no network')
    args = parser.parse_args()
    root, ffprobe, wanted = args.root, args.ffprobe, args.clips
    with open(os.path.join(HERE, 'sarlat_narration.json'), encoding='utf-8') as f:
        narration = json.load(f)
    if ENGINE not in ('edge-tts', 'elevenlabs'):
        parser.error('FM_VOICE_ENGINE must be edge-tts or elevenlabs')
    if set(LANGS) - narration['voices'].keys():
        parser.error('unknown language in FM_LANGS')
    if set(wanted) - narration['clips'].keys():
        parser.error('unknown clip (the consolidated Sarlat film is ln)')
    os.makedirs(os.path.join(root, 'scripts'), exist_ok=True)
    registry = os.path.join(root, 'scripts', 'narration_durations_by_language.json')
    durations = {}
    if os.path.exists(registry):
        with open(registry, encoding='utf-8') as f:
            durations = json.load(f)
    for clip, spec in narration['clips'].items():
        if wanted and clip not in wanted:
            continue
        for lang, voice in narration['voices'].items():
            if lang not in LANGS:
                continue
            os.makedirs(os.path.join(root, 'voice', ENGINE, lang), exist_ok=True)
            for key, texts in spec['lines'].items():
                path = os.path.join(root, 'voice', ENGINE, lang, f'{clip}-{key}.mp3')
                if args.durations_only:
                    if not os.path.isfile(path):
                        parser.error('missing recorded voice: ' + path)
                elif ENGINE == 'elevenlabs':
                    speak_eleven(texts[lang], lang, path)
                else:
                    speak_edge(texts[lang], voice, path)
                d = duration(ffprobe, path)
                durations.setdefault(clip, {}).setdefault(key, {})[lang] = round(d, 2)
                print(f'{clip}-{key} {lang} {d:.1f}s')
    with open(registry, 'w', encoding='utf-8') as f:
        json.dump(durations, f, indent=1)
    longest = {c: {k: max(v.values()) for k, v in lines.items()} for c, lines in durations.items()}
    out = os.path.join(root, 'scripts', 'narration_durations.json')
    merged = {}
    if os.path.exists(out):
        with open(out, encoding='utf-8') as f:
            merged = json.load(f)
    for clip, lines in longest.items():
        for key, seconds in lines.items():
            merged.setdefault(clip, {})[key] = max(merged.get(clip, {}).get(key, 0), seconds)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(merged, f, indent=1)


if __name__ == '__main__':
    main()
