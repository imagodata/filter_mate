# -*- coding: utf-8 -*-
"""User-chosen microphone and transcription destination; no audio is captured by the settings dialog."""
from dataclasses import replace

from qgis.PyQt.QtCore import QCoreApplication, Qt
from qgis.PyQt.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel,
                                 QLineEdit, QPushButton, QVBoxLayout)

from ...core.agent.speech import SERVICES, SpeechSettings, validate_settings


def _tr(text):
    return QCoreApplication.translate('AgentSpeech', text)


class SpeechSettingsDialog(QDialog):
    def __init__(self, values, provider, parent=None, saver=None):
        super().__init__(parent)
        self.setWindowTitle(_tr('Microphone settings'))
        self.setMinimumWidth(420)
        self._original, self._provider, self._saver = values, provider, saver
        self.chosen = None
        self.forget_key = False
        self.service = QComboBox(self)
        for key, label in (('local', 'Local server (OpenAI-compatible)'), ('openai', 'OpenAI'), ('mistral', 'Mistral')):
            self.service.addItem(_tr(label), key)
        self.service.setCurrentIndex(max(0, self.service.findData(values.service)))
        self.address = QLineEdit(values.target, self)
        self.model = QLineEdit(values.chosen_model, self)
        self.language = QLineEdit(values.language, self)
        self.language.setPlaceholderText(_tr('Automatic, or a language code: fr, en…'))
        self.device = QComboBox(self)
        self.device.addItem(_tr('System default microphone'), '')
        try:
            from ...adapters.agent.speech_audio import device_choices
            for key, label in device_choices():
                self.device.addItem(label, key)
        except (ImportError, RuntimeError):
            pass  # capture reports the missing component/device when the user tries to record
        if values.device and self.device.findData(values.device) < 0:
            self.device.addItem(_tr('Previously selected microphone (unavailable)'), values.device)
        self.device.setCurrentIndex(max(0, self.device.findData(values.device)))
        self.key = QLineEdit(self)
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setPlaceholderText(_tr('Stored key') if values.authcfg else '')
        self.reuse_key = QCheckBox(_tr("Use the chat provider's key for this same address"), self)
        self.reuse_key.setChecked(values.use_provider_key)
        self.remove_key = QPushButton(_tr('Remove stored transcription key'), self)
        self.remove_key.setEnabled(bool(values.authcfg))
        self.remove_key.clicked.connect(self._forget)
        self.consent = QCheckBox(_tr('Send recorded audio to this service for transcription'), self)
        self.note = QLabel(self)
        self.note.setWordWrap(True)
        self.note.setTextFormat(Qt.TextFormat.PlainText)
        self.error = QLabel(self)
        self.error.setWordWrap(True)
        self.error.setTextFormat(Qt.TextFormat.PlainText)
        form = QFormLayout()
        for label, widget in (('Transcription service', self.service), ('Service address', self.address),
                              ('Transcription model', self.model), ('Language', self.language),
                              ('Microphone', self.device), ('API key', self.key)):
            form.addRow(_tr(label), widget)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.reuse_key)
        layout.addWidget(self.remove_key)
        layout.addWidget(self.note)
        layout.addWidget(self.consent)
        layout.addWidget(self.error)
        layout.addWidget(buttons)
        self.service.currentIndexChanged.connect(self._service_changed)
        self.address.textChanged.connect(self._destination_changed)
        self.reuse_key.toggled.connect(lambda checked: self.key.setEnabled(not checked))
        self._destination_changed()
        self.key.setEnabled(not self.reuse_key.isChecked())

    def _forget(self):
        self.forget_key = True
        self.key.clear()
        self.key.setPlaceholderText('')
        self.remove_key.setEnabled(False)

    def _service_changed(self, *_):
        base, model = SERVICES[self.service.currentData()]
        self.key.clear()
        self.reuse_key.setChecked(False)
        self.address.setText(base)
        self.model.setText(model)
        self._destination_changed()

    def _destination_changed(self, *_):
        service = self.service.currentData()
        target = self.address.text().strip().rstrip('/')
        cloud = service != 'local'
        self.consent.setVisible(cloud)
        self.consent.setChecked(self._original.accepted_target == target)
        matching = (self._provider.preset == service and self._provider.target == target and self._provider.has_key)
        self.reuse_key.setEnabled(matching)
        if not matching:
            self.reuse_key.setChecked(False)
        if target != self._original.key_target:
            self.key.setPlaceholderText('')
            self.key.clear()
        self.note.setText(_tr('Audio stays in memory and is discarded after transcription. The text is inserted '
                             'in the draft; you review it and press Send yourself.') + '\n' +
            (_tr('Start your local OpenAI-compatible transcription server first. No audio leaves this computer.')
             if not cloud else _tr('The selected service receives the recorded audio and may charge for transcription. '
                                    'Keys are stored in the QGIS authentication database.')))

    def values(self):
        values = SpeechSettings(service=self.service.currentData(), base_url=self.address.text().strip(),
            model=self.model.text().strip(), language=self.language.text().strip().lower(),
            device=self.device.currentData() or '', use_provider_key=self.reuse_key.isChecked())
        return replace(values, accepted_target=values.target if values.service == 'local' or self.consent.isChecked() else '')

    def accept(self):
        try:
            values = self.values()
            validate_settings(values)
            if not values.configured:
                raise ValueError('Choose whether to send recorded audio to this transcription service.')
            if self._saver is None:
                from ...adapters.agent.speech_settings import save_speech_settings
                saver = save_speech_settings
            else:
                saver = self._saver
            self.chosen = saver(values, self.key.text().strip(), forget_key=self.forget_key)
        except (ValueError, RuntimeError) as exc:
            self.error.setText(_tr(str(exc)))
            return
        self.key.clear()
        super().accept()

    def done(self, result):
        self.key.clear()
        super().done(result)
