"""Resize the LinkedIn captures to 1600 px wide: PNG (LinkedIn upload) and WebP (website). Qt does the WebP."""
import os, sys
from qgis.PyQt.QtCore import QCoreApplication, Qt
from qgis.PyQt.QtGui import QImage
app = QCoreApplication(sys.argv)
src, dst = sys.argv[1], sys.argv[2]
os.makedirs(dst, exist_ok=True)
for name in sorted(os.listdir(src)):
    if not name.endswith('.png'):
        continue
    panel = name.endswith('-panel.png')
    img = QImage(os.path.join(src, name)).scaledToWidth(660 if panel else 1600, Qt.TransformationMode.SmoothTransformation)
    stem = name[:-4]
    if not panel:
        img.save(os.path.join(dst, stem + '.jpg'), 'JPG', 88)
    ok = img.save(os.path.join(dst, stem + '.webp'), 'WEBP', 84)
    print(name, img.width(), img.height(), 'webp' if ok else 'NO WEBP',
          os.path.getsize(os.path.join(dst, stem + '.webp')) // 1024 if ok else '-', 'KB')
