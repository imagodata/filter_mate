"""
Layer Settings Dialog (2026-11-24).

Asked once at the opening of a project whose layers carry FilterMate settings that differ from the ones of this
computer: which groups to take from the project (EXPLORING, FILTERING), and whether to ask again for this project.
The project is the truth: both groups are ticked.
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

try:
    from qgis.PyQt.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
    QGIS_AVAILABLE = True
except ImportError:
    QGIS_AVAILABLE = False

GROUP_LABELS = {"exploring": "EXPLORING", "filtering": "FILTERING"}  # the names of the sections of the panel


class LayerSettingsDialog(QDialog):
    """Which settings of the project to apply: one tick per group, a tick to remember, Apply / Keep mine."""

    def __init__(self, groups: List[str], can_remember: bool = True, parent: Optional['QWidget'] = None):
        """Initialize the dialog.

        Args:
            groups: The groups whose settings differ ('exploring', 'filtering').
            can_remember: Offer "Do not ask again for this project" (APP.OPTIONS.LAYER_SETTINGS.remember_answers).
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setObjectName("FilterMateLayerSettingsDialog")
        self.setWindowTitle(self.tr("FilterMate - Settings of the layers"))
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        message = QLabel(self.tr("This project carries FilterMate settings for its layers that differ from yours. "
                                 "Apply the project's settings for:"))
        message.setWordWrap(True)
        layout.addWidget(message)

        self._groups = {}
        for group in groups:
            box = QCheckBox(GROUP_LABELS.get(group, group.upper()))
            box.setObjectName(group)
            box.setChecked(True)  # the project is the truth
            layout.addWidget(box)
            self._groups[group] = box

        self._remember = QCheckBox(self.tr("Do not ask again for this project"))
        self._remember.setObjectName("remember")
        self._remember.setVisible(can_remember)
        self._can_remember = can_remember
        layout.addSpacing(4)
        layout.addWidget(self._remember)

        buttons = QHBoxLayout()
        keep = QPushButton(self.tr("Keep mine"))
        keep.setObjectName("keep")
        keep.clicked.connect(self._keep)
        buttons.addWidget(keep)
        buttons.addStretch()
        apply_button = QPushButton(self.tr("Apply"))
        apply_button.setObjectName("apply")
        apply_button.setDefault(True)
        apply_button.setStyleSheet(  # the primary button of the dialogs of FilterMate (ExportGroupRecapDialog)
            "QPushButton { background: #27ae60; color: white; padding: 8px 16px; "
            "border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background: #219a52; }"
        )
        apply_button.clicked.connect(self.accept)
        buttons.addWidget(apply_button)
        layout.addLayout(buttons)
        self._kept = False
        self._answered = False  # result() is an int in Qt6 and DialogCode an enum: told here

    def accept(self) -> None:
        self._answered = True
        super().accept()

    def _keep(self) -> None:
        """Keep mine: no group taken; the answer may still be remembered."""
        self._kept = True
        self.accept()

    def chosen_groups(self) -> List[str]:
        """The groups to take from the project (none after Keep mine, or when the dialog was closed)."""
        if self._kept or not self._answered:
            return []
        return [group for group, box in self._groups.items() if box.isChecked()]

    def remember(self) -> bool:
        """The answer is kept for this project (a closed dialog answers nothing)."""
        return self._answered and self._can_remember and self._remember.isChecked()
