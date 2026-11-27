"""Bundle only the local data referenced by the delivered QGIS project.

Run after QGIS has finished saving. No profile, authentication database,
provider key, older take or unused dataset enters the folder or archive.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
import xml.etree.ElementTree as ET


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--sources', type=Path, required=True)
    args = parser.parse_args()
    origin = args.project.resolve()
    root = origin.parent
    destination = args.destination.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(origin) as archive:
        document = ET.fromstring(archive.read(next(name for name in archive.namelist() if name.endswith('.qgs'))))
    parents = set()
    for layer in document.findall('.//projectlayers/maplayer'):
        source = layer.findtext('datasource', '').split('|', 1)[0]
        path = (root / source).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError('A layer still depends on a remote or external source: ' + layer.findtext('layername',''))
        parents.add(path.parent)
    for parent in sorted(parents):
        target = destination / parent.relative_to(root)
        target.mkdir(parents=True, exist_ok=True)
        for path in parent.iterdir():
            if path.is_file():
                shutil.copy2(path, target / path.name)
    shutil.copy2(origin, destination / origin.name)
    shutil.copy2(args.sources, destination / 'sources.json')
    inventory = {str(path.relative_to(destination)): {
        'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        for path in sorted(destination.rglob('*')) if path.is_file()}
    (destination / 'manifest.json').write_text(json.dumps({
        'project':origin.name,'scope':'Referenced local data and saved QGIS styles, filters and layout',
        'publication':'not_published','files':inventory}, ensure_ascii=False,indent=2)+'\n')
    output = destination.parent / 'urumea-projet-portable.zip'
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in sorted(destination.rglob('*')):
            if path.is_file():archive.write(path,path.relative_to(destination.parent))
    print(json.dumps({'folder':str(destination),'archive':str(output),'files':len(inventory),
                      'bytes':output.stat().st_size,'sha256':hashlib.sha256(output.read_bytes()).hexdigest()},indent=2))


if __name__ == '__main__':
    main()
