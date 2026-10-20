"""Validate a plugin archive and upload it using QGIS's XML-RPC API."""

import argparse
import ast
import base64
import configparser
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess  # nosec B404 - argument lists, never a shell
import sys
import tempfile
import xmlrpc.client
import zipfile


# What plugins.qgis.org refuses or flags (and what has no business in a release archive).
FORBIDDEN_EXTENSIONS = ('.pyc', '.pyo', '.pyd', '.log', '.so', '.dll', '.dylib', '.exe')
MAX_ARCHIVE_BYTES = 20 * 1024 * 1024          # the repository accepts 25 MB; keep a margin
MAX_UNPACKED_BYTES = 100 * 1024 * 1024
MAX_ENTRY_BYTES = 25 * 1024 * 1024            # one file (a stray database or video)
REQUIRED_METADATA = ('name', 'qgisMinimumVersion', 'description', 'about', 'version', 'author', 'email',
                     'repository', 'tracker', 'icon')
PLUGIN_FOLDER = 'filter_mate'


def _load_qt_enum_scan():
    """scripts/qt_enum_scan.py: the detector the unit tests use, run here on the archive content."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import qt_enum_scan
    return qt_enum_scan


def check_archive_content(archive):
    """Refuse forbidden file types, oversized archives and entries. Returns the list of problems."""
    problems = []
    infos = [info for info in archive.infolist() if not info.is_dir()]
    for info in infos:
        if info.filename.lower().endswith(FORBIDDEN_EXTENSIONS):
            problems.append(f'forbidden file type: {info.filename}')
        if info.file_size > MAX_ENTRY_BYTES:
            problems.append(f'file larger than {MAX_ENTRY_BYTES // 2**20} MB: {info.filename}')
    unpacked = sum(info.file_size for info in infos)
    if unpacked > MAX_UNPACKED_BYTES:
        problems.append(f'unpacked size {unpacked // 2**20} MB exceeds {MAX_UNPACKED_BYTES // 2**20} MB')
    return problems


def check_metadata(metadata, archive):
    """Mandatory plugins.qgis.org keys, present and not empty; the icon file must be shipped."""
    problems = []
    if not metadata.has_section('general'):
        return ['metadata.txt has no [general] section']
    general = metadata['general']
    for key in REQUIRED_METADATA:
        if not general.get(key, '').strip():
            problems.append(f'metadata.txt: missing or empty "{key}"')
    icon = general.get('icon', '').strip()
    if icon and f'{PLUGIN_FOLDER}/{icon}' not in archive.namelist():
        problems.append(f'metadata.txt: icon "{icon}" is not in the archive')
    return problems


def check_python_sources(archive):
    """Python 3.8 grammar (QGIS 3.22) and no unscoped Qt enum (Qt6 check of the repository)."""
    scan = _load_qt_enum_scan()
    problems = []
    for name in archive.namelist():
        if not name.endswith('.py'):
            continue
        try:
            source = archive.read(name).decode('utf-8')
            ast.parse(source, filename=name, feature_version=(3, 8))
            offences = scan.scan_source(source, name)
        except (SyntaxError, UnicodeDecodeError, ValueError) as exc:
            problems.append(f'{name}: {exc}')
            continue
        problems.extend(f'{name}:{lineno} unscoped Qt enum {spelling}' for lineno, spelling in offences)
    return problems


def _scanner_command(module, uvx_args, tools_dir):
    """argv prefix running a scanner: the installed module, else uvx, else pip into ``tools_dir``."""
    if importlib.util.find_spec(module):
        return [sys.executable, '-m', module], None
    if shutil.which('uvx'):
        return ['uvx'] + uvx_args, None
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet', '--target', str(tools_dir), uvx_args[-1]],  # nosec B603 - fixed argv
                   check=True, capture_output=True, timeout=300)
    return [sys.executable, '-m', module], {**os.environ, 'PYTHONPATH': str(tools_dir)}


def bandit_problems(report):
    """Findings of a ``bandit -f json`` report as readable problems (B404, ``import subprocess``, is ignored
    by the repository, which flags everything else whatever its severity)."""
    return [f"Bandit {item['test_id']} {item['filename']}:{item['line_number']} {item['issue_text']}"
            for item in report.get('results', []) if item.get('test_id') != 'B404']


def secrets_problems(report):
    """Findings of a ``detect-secrets scan`` report."""
    return [f'detect-secrets {item.get("type")} {name}:{item.get("line_number")}'
            for name, items in report.get('results', {}).items() for item in items]


# plugins.qgis.org runs flake8 on the archive without the repository's .flake8; these are the repository's own
# ignores (.flake8), so what is left is what the site would report (E731, F401...).
FLAKE8_ARGS = ['--isolated', '--max-line-length=200',
               '--ignore=E701,E702,E704,E402,E117,E123,E125,E127,E128,W503,W504,F824,E241,E261',
               '--per-file-ignores=__init__.py:F401 filter_mate.py:F403']


def flake8_problems(output):
    """Lines of a default-format flake8 report (``path:line:col: CODE message``) as problems."""
    return [f'flake8 {line}' for line in output.splitlines() if line.strip()]


def check_security(archive):
    """What plugins.qgis.org runs on an upload and blocks the version for, whatever the severity: Bandit,
    detect-secrets and flake8 on the unpacked archive. A ``# nosec Bxxx`` or ``# pragma: allowlist secret`` comment
    with its reason is the way to accept a false positive."""
    with tempfile.TemporaryDirectory() as work:
        root = Path(work) / 'src'
        archive.extractall(root)
        tools = Path(work) / 'tools'
        problems = []
        bandit, env = _scanner_command('bandit', ['bandit'], tools)
        run = subprocess.run(bandit + ['-r', PLUGIN_FOLDER, '-f', 'json', '-q'], cwd=root, env=env,  # nosec B603 - fixed argv
                             capture_output=True, text=True, timeout=600)
        problems += bandit_problems(json.loads(run.stdout or '{}'))
        secrets, env = _scanner_command('detect_secrets', ['--from', 'detect-secrets', 'detect-secrets'], tools)
        run = subprocess.run(secrets + ['scan', '--all-files', PLUGIN_FOLDER], cwd=root, env=env,  # nosec B603 - fixed argv
                             capture_output=True, text=True, timeout=600)
        problems += secrets_problems(json.loads(run.stdout or '{}'))
        flake8, env = _scanner_command('flake8', ['flake8'], tools)
        run = subprocess.run(flake8 + FLAKE8_ARGS + [PLUGIN_FOLDER], cwd=root, env=env,  # nosec B603 - fixed argv
                             capture_output=True, text=True, timeout=600)
        problems += flake8_problems(run.stdout)
    return problems


def validate(path, security=False):
    path = Path(path)
    if path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError(f'Archive larger than {MAX_ARCHIVE_BYTES // 2**20} MB')
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError('Corrupt ZIP archive')
        for name in archive.namelist():
            parts = Path(name).parts
            if not parts or parts[0] != PLUGIN_FOLDER or '..' in parts:
                raise ValueError('Unexpected archive path')
        metadata = configparser.ConfigParser()
        metadata.read_string(archive.read(f'{PLUGIN_FOLDER}/metadata.txt').decode('utf-8'))
        for section in metadata.sections():
            for key in metadata[section]:
                metadata.get(section, key)
        entry = ast.parse(archive.read(f'{PLUGIN_FOLDER}/__init__.py'))
        if not any(isinstance(node, ast.FunctionDef) and node.name == 'classFactory'
                   for node in entry.body):
            raise ValueError('Missing classFactory entry point')
        archive.getinfo(f'{PLUGIN_FOLDER}/filter_mate.py')
        problems = check_archive_content(archive) + check_metadata(metadata, archive) + check_python_sources(archive)
        if security:
            problems += check_security(archive)
        if problems:
            shown = '\n  '.join(problems[:50])
            more = f'\n  ... and {len(problems) - 50} more' if len(problems) > 50 else ''
            raise ValueError(f'Archive rejected ({len(problems)} problem(s)):\n  {shown}{more}')
        return metadata.get('general', 'version')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--skip-security-scan', action='store_true',
                        help='do not run Bandit and detect-secrets (the repository runs them on every upload)')
    args = parser.parse_args()
    version = validate(args.archive, security=not args.skip_security_scan)
    print(f'Validated FilterMate {version}: ZIP structure, entry point, metadata keys, file types, size, '
          'Python 3.8 syntax and Qt enums' + ('' if args.skip_security_scan else ', Bandit, detect-secrets and flake8'))
    if args.validate_only:
        return
    username = os.environ.get('OSGEO_USERNAME', '')
    password = os.environ.get('OSGEO_PASSWORD', '')
    if not username or not password:
        raise ValueError('OSGEO_USERNAME and OSGEO_PASSWORD are required')
    authorization = base64.b64encode(f'{username}:{password}'.encode()).decode()
    # Keep credentials out of URLs and exception representations.
    with xmlrpc.client.ServerProxy(
        'https://plugins.qgis.org/plugins/RPC2/',
        headers=[('Authorization', f'Basic {authorization}')],
    ) as server:
        try:
            result = server.plugin.upload(xmlrpc.client.Binary(args.archive.read_bytes()))
        except xmlrpc.client.Fault as exc:
            message = exc.faultString.replace(password, '[redacted]').replace(username, '[redacted]')
            raise RuntimeError(f'QGIS upload rejected ({exc.faultCode}): {message}') from None
    print(f'QGIS accepted upload for {version}: {result}. Publication may require approval.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
