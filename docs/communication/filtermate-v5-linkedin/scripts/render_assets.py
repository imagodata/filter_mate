"""Export native QGIS captures for publication. Run with QGIS's Python/Qt."""
from pathlib import Path
import json
import os
import shutil

from qgis.PyQt.QtCore import Qt, QRectF
from qgis.PyQt.QtGui import QColor, QFont, QFontDatabase, QImage, QLinearGradient, QPainter
from qgis.PyQt.QtWidgets import QApplication

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
app = QApplication([])
for font_file in ('segoeui.ttf', 'segoeuib.ttf'):
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + font_file)

ROOT = Path(os.environ.get('FM5_PUBLICATION_ROOT', Path(__file__).resolve().parent.parent))
CAP = ROOT / 'screenshots'
stems = [
    '00_sarlat_overview', '01_roads_buildings', '02_church_dtm_lidar',
    '03_slope_parcels', '04_ndvi_parcels', '05_high_vegetation_roads',
]
titles = [
    'Complete source layers', 'A named street corridor', 'One DTM and LiDAR boundary',
    'Slope and parcel coverage', 'NDVI and parcel coverage', 'Vegetation near the boulevard',
]
exports = []
for file in sorted(CAP.glob('*.png')):
    img = QImage(str(file))
    if img.isNull():
        raise RuntimeError('Unreadable image: ' + str(file))
    # Keep native full-window and widget resolution; scale map-only exports if needed.
    if file.stem.endswith(('-map', '-terrain')) and img.width() > 2000:
        img = img.scaledToWidth(2000, Qt.TransformationMode.SmoothTransformation)
    dest = file.with_suffix('.jpg')
    if not img.save(str(dest), 'JPG', 97 if file.stem.endswith(('-settings', '-panel')) else 95):
        raise RuntimeError('Could not save ' + str(dest))
    exports.append({'file': str(dest.relative_to(ROOT)).replace('\\', '/'),
                    'width': img.width(), 'height': img.height()})


def fitted(painter, image, rect):
    scale = min(rect.width() / image.width(), rect.height() / image.height())
    width, height = image.width() * scale, image.height() * scale
    target = QRectF(rect.x() + (rect.width() - width) / 2,
                    rect.y() + (rect.height() - height) / 2, width, height)
    painter.drawImage(target, image)


sheet = QImage(1960, 2200, QImage.Format.Format_RGB32)
sheet.fill(QColor('#eaf0f2'))
p = QPainter(sheet)
p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
p.setPen(QColor('#173b45'))
p.setFont(QFont('Segoe UI', 26, QFont.Weight.Bold))
p.drawText(QRectF(28, 16, 1900, 56), Qt.AlignmentFlag.AlignLeft,
           'FilterMate 5 — full QGIS captures')
for i, (stem, title) in enumerate(zip(stems, titles)):
    x, y = 24 + i % 2 * 970, 90 + i // 2 * 695
    fitted(p, QImage(str(CAP / (stem + '.jpg'))), QRectF(x, y, 942, 644))
    p.setFont(QFont('Segoe UI', 18))
    p.drawText(QRectF(x, y + 649, 942, 38), Qt.AlignmentFlag.AlignLeft,
               f'{i:02d}  {title}')
p.end()
sheet.save(str(ROOT / 'screenshots-overview.jpg'), 'JPG', 94)

cover = QImage(1920, 1080, QImage.Format.Format_RGB32)
p = QPainter(cover)
p.setRenderHint(QPainter.RenderHint.Antialiasing)
p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
gradient = QLinearGradient(0, 0, 1920, 1080)
gradient.setColorAt(0, QColor('#102a35'))
gradient.setColorAt(1, QColor('#224a4a'))
p.fillRect(cover.rect(), gradient)
p.setPen(Qt.PenStyle.NoPen)
p.setBrush(QColor('#9de0b3'))
p.drawRoundedRect(QRectF(75, 75, 274, 57), 28, 28)
p.setPen(QColor('#12372d'))
p.setFont(QFont('Segoe UI', 22, QFont.Weight.Bold))
p.drawText(QRectF(75, 75, 274, 57), Qt.AlignmentFlag.AlignCenter, 'FILTERMATE 5')
p.setPen(QColor('white'))
p.setFont(QFont('Segoe UI', 48, QFont.Weight.Bold))
p.drawText(QRectF(75, 205, 710, 330), Qt.TextFlag.TextWordWrap,
           'Vectors, rasters and LiDAR in QGIS')
p.setPen(QColor('#bcd5d4'))
p.setFont(QFont('Segoe UI', 25))
p.drawText(QRectF(79, 610, 670, 170), Qt.TextFlag.TextWordWrap,
           'Five practical workflows.\nEvery setting visible.')
fitted(p, QImage(str(CAP / '01_roads_buildings.jpg')), QRectF(840, 180, 1010, 730))
p.setPen(QColor('#a5cec6'))
p.setFont(QFont('Segoe UI', 21))
p.drawText(QRectF(76, 955, 1768, 65), Qt.AlignmentFlag.AlignLeft,
           'Free and open source  ·  Sarlat-la-Canéda  ·  Real QGIS screenshots')
p.end()
cover.save(str(ROOT / 'linkedin-cover.jpg'), 'JPG', 95)

# Native local working copy for Chromium's PDF printer. No GIS files are modified.
work = Path(os.environ.get('TEMP', '.')) / 'fm-linkedin-sarlat' / 'publication'
(work / 'screenshots').mkdir(parents=True, exist_ok=True)
shutil.copy2(ROOT / 'linkedin-article.html', work / 'linkedin-article.html')
for file in CAP.glob('*.jpg'):
    shutil.copy2(file, work / 'screenshots' / file.name)
(ROOT / 'image-exports.json').write_text(json.dumps(exports, indent=2), encoding='utf-8')
print(f'Exported {len(exports)} JPEGs, overview and cover; PDF source: {work}')
