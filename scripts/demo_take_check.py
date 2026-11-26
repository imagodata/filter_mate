#!/usr/bin/env python3
"""Check capture integrity before rendering. This does not certify scenario claims."""
import argparse
import json
from pathlib import Path
import sys


def check(folder):
    errors = []
    if (folder / 'failure.json').exists():
        errors.append('failure.json exists')
    try:
        meta = json.loads((folder / 'meta.json').read_text(encoding='utf-8'))
        times = meta['frames']
        if meta.get('status') != 'complete':
            errors.append('capture was not completed by the reconciled recorder')
        if not times or any(b <= a for a, b in zip(times, times[1:])):
            errors.append('empty or non-monotonic frame clock')
        for i in range(len(times)):
            path = folder / 'frames' / f'{i:06d}.jpg'
            if not path.is_file() or path.stat().st_size == 0:
                errors.append(f'missing frame {i}')
                break
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(str(exc))
    try:
        log = (folder / 'capture.log').read_text(encoding='utf-8')
        if 'Traceback' in log or 'CAPTURE FAILED' in log:
            errors.append('exception in capture.log')
        if 'stopped:' not in log:
            errors.append('no recording completion in capture.log')
    except OSError as exc:
        errors.append(str(exc))
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    errors = check(args.folder)
    print(json.dumps({'capture_integrity': 'failed' if errors else 'passed', 'errors': errors}))
    return int(bool(errors))


if __name__ == '__main__':
    sys.exit(main())
