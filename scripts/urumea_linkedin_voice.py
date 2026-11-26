#!/usr/bin/env python3
"""Generate the French Urumea voice tracks and their measured durations.

Usage: python3 scripts/urumea_linkedin_voice.py WORK --ffprobe ffprobe
Reads WORK/voice/narration.fr.json. Requires edge-tts and ffprobe.
"""
import argparse
import asyncio
import json
from pathlib import Path
import subprocess


async def generate(root, probe):
    import edge_tts
    folder = root / 'voice'
    spec = json.loads((folder / 'narration.fr.json').read_text(encoding='utf-8'))
    durations = {}
    for line in spec['lines']:
        path = folder / (line['id'] + '.mp3')
        if not path.is_file() or path.stat().st_size < 1000:
            await asyncio.wait_for(edge_tts.Communicate(
                line['text'], spec['voice'], rate=spec.get('rate', '+0%'),
                connect_timeout=10, receive_timeout=30).save(str(path)), timeout=50)
        info = json.loads(subprocess.check_output([
            probe, '-v', 'error', '-show_entries',
            'format=duration:stream=codec_name,sample_rate,channels', '-of', 'json', str(path)], text=True))
        durations[line['id']] = {'duration_s': float(info['format']['duration']), **info['streams'][0]}
        print(line['id'], durations[line['id']]['duration_s'])
    (folder / 'durations.json').write_text(json.dumps(durations, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--ffprobe', default='ffprobe')
    args = parser.parse_args()
    asyncio.run(generate(args.root, args.ffprobe))


if __name__ == '__main__':
    main()
