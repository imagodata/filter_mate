# -*- coding: utf-8 -*-
"""Microphone capture -> transcription -> editable draft. It never submits an agent request."""
import time

from qgis.PyQt.QtCore import QCoreApplication, QObject, QTimer
from qgis.PyQt.QtWidgets import QDialog

from ...adapters.agent.speech_settings import load_speech_settings, speech_key
from ...core.agent.speech import MAX_SECONDS, transcription_request, validate_settings


def _tr(text):
    return QCoreApplication.translate('AgentSpeech', text)


class AgentSpeechController(QObject):
    def __init__(self, host, capture_factory=None, request_factory=None):
        super().__init__(host.panel)
        self.host = host
        self._capture_factory, self._request_factory = capture_factory, request_factory
        self._capture = self._request = None
        self._settings = None
        self._key = ''
        self._generation = 0
        self._closed = False
        self._started = None
        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._tick)
        host.panel.destroyed.connect(self.close)

    def settings(self):
        self.cancel()
        from ..widgets.agent_speech import SpeechSettingsDialog
        from ...adapters.agent.settings import load_settings
        dialog = SpeechSettingsDialog(load_speech_settings(), load_settings(), self.host.panel)
        try:
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.host.panel.set_status(_tr('Microphone configured. Click the microphone to dictate.'))
                return True
        finally:
            dialog.key.clear()
            dialog.deleteLater()
        return False

    def toggle(self):
        if self._closed:
            return
        if self.host.panel._speech_state == 'recording':
            self.transcribe()
            return
        if self.host.panel._speech_state == 'transcribing':
            self.cancel()
            return
        values = load_speech_settings()
        if not values.configured:
            self.settings()
            return
        try:
            validate_settings(values)
            key = speech_key(values)
            if values.service != 'local' and not key:
                raise ValueError('This transcription service needs an API key.')
            self._generation += 1
            generation = self._generation
            self._settings, self._key = values, key
            if self._capture_factory is None:
                from ...adapters.agent.speech_audio import AudioCapture
                factory = AudioCapture
            else:
                factory = self._capture_factory
            self._capture = factory(lambda: self._listening(generation),
                lambda error: self._fail(error) if generation == self._generation else None,
                lambda: self.transcribe() if generation == self._generation else None, self)
            self.host.panel.set_speech_state('recording', _tr('Requesting microphone access…'), can_transcribe=False)
            self._capture.start(values.device)
        except (ValueError, RuntimeError, ImportError) as exc:
            self._fail(str(exc))

    def _listening(self, generation):
        if self._closed or generation != self._generation:
            return
        self._started = time.monotonic()
        self._timer.start()
        self._tick()

    def _tick(self):
        if self._started is None or self._settings is None:
            return
        seconds = int(time.monotonic() - self._started)
        if seconds >= MAX_SECONDS:
            self.transcribe()
            return
        label = {'local': _tr('Local service'), 'openai': 'OpenAI', 'mistral': 'Mistral'}[self._settings.service]
        self.host.panel.set_speech_state('recording', _tr('Recording… {} · {}').format(
            f'{seconds // 60}:{seconds % 60:02} / {MAX_SECONDS // 60}:{MAX_SECONDS % 60:02}', label))

    def transcribe(self):
        if self._capture is None or self._closed:
            return
        self._timer.stop()
        self._started = None
        capture, self._capture = self._capture, None
        generation = self._generation
        try:
            wav = capture.stop()
            capture.deleteLater()
            if self._closed or generation != self._generation:
                return
            request = transcription_request(self._settings, wav, self._key)
            self._key = ''
            self.host.panel.set_speech_state('transcribing', _tr('Transcribing…'))
            if self._request_factory is None:
                from ...adapters.agent.speech_transport import SpeechRequest
                factory = SpeechRequest
            else:
                factory = self._request_factory
            self._request = factory(request, lambda text, error: self._done(generation, text, error), self)
        except (ValueError, RuntimeError, ImportError) as exc:
            capture.cancel()
            capture.deleteLater()
            self._fail(str(exc))

    def _done(self, generation, text, error):
        if self._closed or generation != self._generation:
            return
        self._request = None
        self._settings = None
        self.host.panel.set_speech_state('idle')
        if error:
            self._fail(error)
        elif text:
            self.host.panel.insert_transcription(text)
            self.host.panel.set_status(_tr('Dictation added to the draft. Review it, then press Send.'))

    def _fail(self, error):
        if self._closed:
            return
        self.cancel()
        self.host.panel.set_status(_tr('Microphone: {}').format(_tr(error)), error=True)

    def cancel(self, update=True):
        self._generation += 1
        self._timer.stop()
        self._started = None
        capture, request = self._capture, self._request
        self._capture = self._request = None
        self._settings, self._key = None, ''
        if capture is not None:
            capture.cancel()
            capture.deleteLater()
        if request is not None:
            request.abort()
        if update and not self._closed:
            self.host.panel.set_speech_state('idle')

    def close(self, *_):
        self._closed = True
        self.cancel(update=False)
