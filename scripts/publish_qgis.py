"""Validate a plugin archive and upload it using QGIS's XML-RPC API."""

import argparse
import ast
import base64
import configparser
import os
from pathlib import Path
import sys
import xmlrpc.client
import zipfile


def validate(path):
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError('Corrupt ZIP archive')
        for name in archive.namelist():
            parts = Path(name).parts
            if not parts or parts[0] != 'filter_mate' or '..' in parts:
                raise ValueError('Unexpected archive path')
        metadata = configparser.ConfigParser()
        metadata.read_string(archive.read('filter_mate/metadata.txt').decode('utf-8'))
        for section in metadata.sections():
            for key in metadata[section]:
                metadata.get(section, key)
        entry = ast.parse(archive.read('filter_mate/__init__.py'))
        if not any(isinstance(node, ast.FunctionDef) and node.name == 'classFactory'
                   for node in entry.body):
            raise ValueError('Missing classFactory entry point')
        archive.getinfo('filter_mate/filter_mate.py')
        return metadata.get('general', 'version')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    version = validate(args.archive)
    print(f'Validated FilterMate {version}: metadata, ZIP structure and entry point')
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
