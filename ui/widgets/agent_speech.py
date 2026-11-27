# -*- coding: utf-8 -*-
"""Microphone settings and an explicit, bounded recording/transcription test."""
from dataclasses import replace
from functools import partial
import time

from qgis.PyQt.QtCore import QCoreApplication, QTimer, Qt
from qgis.PyQt.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
                                 QLabel, QLineEdit, QPlainTextEdit, QProgressBar, QPushButton, QVBoxLayout)

from ...core.agent.speech import SERVICES, SpeechSettings, transcription_request, validate_settings


def _tr(text):
    return QCoreApplication.translate('AgentSpeech', text)


class SpeechSettingsDialog(QDialog):
    def __init__(self, values, provider, parent=None, saver=None, capture_factory=None, request_factory=None):
        super().__init__(parent)
        self.setWindowTitle(_tr('Microphone settings'))
        self.setMinimumWidth(420)
        self._original, self._provider, self._saver = values, provider, saver
        self.chosen = None
        self.forget_key = False
        self._capture_factory, self._request_factory = capture_factory, request_factory
        self._test_capture = self._test_request = None
        self._test_wav = b''
        self._test_started = None
        self._test_generation = 0
        self._test_timer = QTimer(self)
        self._test_timer.setInterval(100)
        self._test_timer.timeout.connect(self._test_tick)
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
        self.test_microphone = QPushButton(_tr('Test microphone'), self)
        self.test_microphone.clicked.connect(self._toggle_test)
        self.test_transcription = QPushButton(_tr('Test transcription'), self)
        self.test_transcription.setEnabled(False)
        self.test_transcription.clicked.connect(self._transcribe_test)
        self.test_level = QProgressBar(self)
        self.test_level.setRange(0, 100)
        self.test_level.setValue(0)
        self.test_level.setFormat(_tr('Microphone level: %p%'))
        self.test_status = QLabel(_tr('Record up to 10 seconds, then test transcription with the settings above.'), self)
        self.test_status.setWordWrap(True)
        self.test_status.setTextFormat(Qt.TextFormat.PlainText)
        self.test_result = QPlainTextEdit(self)
        self.test_result.setReadOnly(True)
        self.test_result.setMaximumHeight(85)
        self.test_result.hide()
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
        test_buttons = QHBoxLayout()
        test_buttons.addWidget(self.test_microphone)
        test_buttons.addWidget(self.test_transcription)
        layout.addLayout(test_buttons)
        layout.addWidget(self.test_level)
        layout.addWidget(self.test_status)
        layout.addWidget(self.test_result)
        layout.addWidget(self.error)
        layout.addWidget(buttons)
        self.service.currentIndexChanged.connect(self._service_changed)
        self.address.textChanged.connect(self._destination_changed)
        self.reuse_key.toggled.connect(lambda checked: self.key.setEnabled(not checked))
        self._destination_changed()
        self.key.setEnabled(not self.reuse_key.isChecked())
        for widget in (self.address, self.model, self.language, self.key):
            widget.textChanged.connect(self._test_settings_changed)
        self.reuse_key.toggled.connect(self._test_settings_changed)
        self.consent.toggled.connect(self._test_settings_changed)

    def _test_settings_changed(self, *_):
        if self._test_request is not None or not self.test_result.isHidden():
            self._reset_test(discard=False)
            self.test_result.clear()
            self.test_result.hide()
            self.test_status.setText(_tr('Settings changed. Test transcription again.'))

    def _reset_test(self, *, discard=True):
        self._test_generation += 1
        self._test_timer.stop()
        self._test_started = None
        capture, request = self._test_capture, self._test_request
        self._test_capture = self._test_request = None
        if capture is not None:
            capture.cancel()
            capture.deleteLater()
        if request is not None:
            request.abort()
        if discard:
            self._test_wav = b''
        self.device.setEnabled(True)
        self.test_level.setValue(0)
        self.test_microphone.setText(_tr('Test microphone'))
        self.test_transcription.setEnabled(bool(self._test_wav))

    def _test_error(self, generation, error):
        if generation != self._test_generation:
            return
        self._reset_test()
        self.test_status.setText(_tr(error))

    def _toggle_test(self):
        if self._test_capture is not None:
            self._stop_test()
            return
        if self._test_request is not None:
            self._reset_test()
            self.test_status.setText(_tr('Test cancelled.'))
            return
        self._reset_test()
        self.test_result.clear()
        self.test_result.hide()
        generation = self._test_generation
        try:
            factory = self._capture_factory
            if factory is None:
                from ...adapters.agent.speech_audio import AudioCapture
                factory = partial(AudioCapture, max_seconds=10)
            self._test_capture = factory(lambda: self._test_listening(generation),
                lambda error: self._test_error(generation, error),
                lambda: self._stop_test() if generation == self._test_generation else None, self)
            self.device.setEnabled(False)
            self.test_microphone.setText(_tr('Stop microphone test'))
            self.test_status.setText(_tr('Requesting microphone access…'))
            self._test_capture.start(self.device.currentData() or '')
        except (ValueError, RuntimeError, ImportError) as exc:
            self._test_error(generation, str(exc))

    def _test_listening(self, generation):
        if generation != self._test_generation:
            return
        self._test_started = time.monotonic()
        self._test_timer.start()
        self._test_tick()

    def _test_tick(self):
        if self._test_capture is None or self._test_started is None:
            return
        seconds = time.monotonic() - self._test_started
        if seconds >= 10:
            self._stop_test()
            return
        self.test_level.setValue(round(self._test_capture.level * 100))
        self.test_status.setText(_tr('Speak into the microphone… {} / 10 s').format(int(seconds)))

    def _stop_test(self):
        capture, self._test_capture = self._test_capture, None
        if capture is None:
            return
        generation = self._test_generation
        try:
            wav = capture.stop()
            if generation != self._test_generation:
                return
            self._test_wav = wav
            self._reset_test(discard=False)
            self.test_status.setText(_tr('Recording ready. Click Test transcription to check the service.'))
        except (ValueError, RuntimeError) as exc:
            capture.cancel()
            self._test_error(self._test_generation, str(exc))
        finally:
            capture.deleteLater()

    def _transcribe_test(self):
        if not self._test_wav or self._test_request is not None:
            return
        generation = self._test_generation
        try:
            from ...adapters.agent.speech_settings import speech_key
            values = self.values()
            validate_settings(values)
            if not values.configured:
                raise ValueError('Choose whether to send recorded audio to this transcription service.')
            # Test the unsaved form without writing settings or credentials.
            if not self.forget_key and values.target == self._original.key_target:
                values = replace(values, authcfg=self._original.authcfg, key_target=self._original.key_target)
            key = speech_key(values) if values.use_provider_key else self.key.text().strip() or speech_key(values)
            request = transcription_request(values, self._test_wav, key)
            factory = self._request_factory
            if factory is None:
                from ...adapters.agent.speech_transport import SpeechRequest
                factory = SpeechRequest
            self.test_transcription.setEnabled(False)
            self.test_result.clear()
            self.test_result.hide()
            self.test_microphone.setText(_tr('Cancel transcription'))
            self.test_status.setText(_tr('Transcribing…'))
            self._test_request = factory(request,
                lambda text, error: self._test_done(generation, text, error), self)
        except (ValueError, RuntimeError, ImportError) as exc:
            # Keep the recording so the user can correct the settings and retry.
            self._reset_test(discard=False)
            self.test_status.setText(_tr(str(exc)))

    def _test_done(self, generation, text, error):
        if generation != self._test_generation:
            return
        self._test_request = None
        self._reset_test(discard=False)
        self.test_status.setText(_tr(error) if error else _tr('Transcription test succeeded.'))
        if not error:
            self.test_result.setPlainText(text)
            self.test_result.show()

    def _forget(self):
        self._test_settings_changed()
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
        self._reset_test()
        self.test_result.clear()
        self.key.clear()
        super().done(result)
