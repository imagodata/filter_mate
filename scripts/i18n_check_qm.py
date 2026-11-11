"""Load each i18n/FilterMate_*.qm with QTranslator and print how it translates the given (context, source) pairs.

Run in a qgis/qgis image: QT_QPA_PLATFORM=offscreen python3 scripts/i18n_check_qm.py Context "source" [...]
Exits 1 when a .qm does not load or leaves a message untranslated (English excepted).
"""
import glob
import os
import sys

from qgis.PyQt.QtCore import QCoreApplication, QTranslator

app = QCoreApplication(sys.argv[:1])
pairs = list(zip(sys.argv[1::2], sys.argv[2::2]))
failed = False
for path in sorted(glob.glob(os.path.join("i18n", "FilterMate_*.qm"))):
    translator = QTranslator()
    if not translator.load(path):
        print(f"FAIL {path}: not loaded")
        failed = True
        continue
    code = os.path.basename(path)[len("FilterMate_"):-len(".qm")]
    for context, source in pairs:
        # PyQt hands a str to QTranslator.translate as ASCII; self.tr sends UTF-8, so a source with π or × goes as bytes
        text = translator.translate(context.encode("utf-8"), source.encode("utf-8"))
        if not text and code != "en":
            failed = True
        print(f"{code:4} {text or 'UNTRANSLATED'}")
sys.exit(1 if failed else 0)
