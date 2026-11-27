"""Speech dictation with real Qt widgets/networking, deterministic PCM, and no actual microphone or paid API."""
import json
import os
import struct
import sys
import tempfile
import threading
import time
import traceback
import types
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import patch

sys.dont_write_bytecode = True
package = types.ModuleType('filter_mate')
package.__path__ = [os.environ.get('FM_REPO', '/src')]
sys.modules['filter_mate'] = package
os.environ['FILTERMATE_LOG_DIR'] = tempfile.mkdtemp(prefix='fm-speech-logs-')

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QByteArray, QBuffer, QIODevice, QObject, QTimer, pyqtSignal
from qgis.PyQt.QtGui import QTextCursor
from qgis.PyQt.QtNetwork import QNetworkProxy
app = QgsApplication([], False)
app.initQgis()


def check(label, condition):
    assert condition, label
    print('PASS ' + label, flush=True)


def until(condition, timeout=5):
    end = time.monotonic() + timeout
    while not condition() and time.monotonic() < end:
        app.processEvents()
        time.sleep(0.005)
    assert condition(), 'timed out waiting for a Qt operation'


def main():
    from filter_mate.core.agent.speech import MAX_RESPONSE_BYTES, SERVICES, SpeechSettings, transcription_request
    from filter_mate.adapters.agent import speech_audio, speech_transport
    from filter_mate.ui.controllers import agent_speech as controller
    from filter_mate.ui.widgets.agent_panel import AgentPanel
    from filter_mate.ui.widgets.agent_speech import SpeechSettingsDialog
    from filter_mate.adapters.agent.settings import AgentSettings

    raw = struct.pack('<h', 2000) * 5000
    media = speech_audio._multimedia()
    qt6 = hasattr(media, 'QAudioSource')

    class Source(QObject):
        stateChanged = pyqtSignal(object)

        def __init__(self, device, audio_format, parent):
            super().__init__(parent)
            self.audio_format = audio_format
            self.io = QBuffer(self)
            self.io.setData(QByteArray(raw))
            self.io.open(QIODevice.OpenModeFlag.ReadOnly)

        def start(self):
            return self.io

        def stop(self):
            pass

        def error(self):
            return 0

    fake_media = SimpleNamespace(QAudioFormat=media.QAudioFormat, QAudioInput=Source, QAudioSource=Source)
    device = SimpleNamespace(isNull=lambda: False, isFormatSupported=lambda value: True)
    errors, starts = [], []
    capture = speech_audio.AudioCapture(lambda: starts.append(True), errors.append, lambda: None)
    with patch.object(speech_audio, '_devices', return_value=(fake_media, [device], device, qt6)):
        capture.start()
        until(lambda: bool(starts) or bool(errors))
        check('Qt audio format and capture start work', bool(starts) and not errors)
        wav = capture.stop()
    check('microphone PCM becomes a WAV held only in memory', wav.startswith(b'RIFF') and len(wav) > 44
          and capture.buffer is None and capture._source is None)
    limited = speech_audio.AudioCapture(lambda: None, errors.append, lambda: None, max_seconds=0.2)
    with patch.object(speech_audio, '_devices', return_value=(fake_media, [device], device, qt6)):
        limited.start()
        short_wav = limited.stop()
    check('test capture duration is bounded by the audio samples as well as the UI timer',
          len(short_wav) == 44 + 3200 * 2)
    if qt6:
        denied = SimpleNamespace(checkPermission=lambda _: speech_audio.Qt.PermissionStatus.Denied)
        with patch.object(speech_audio, 'QCoreApplication', SimpleNamespace(instance=lambda: denied)):
            try:
                capture.start()
            except ValueError as exc:
                check('denied OS microphone permission is reported without capturing audio', 'denied' in str(exc))
            else:
                raise AssertionError('denied permission must not record')
        callbacks = []
        pending = SimpleNamespace(checkPermission=lambda _: speech_audio.Qt.PermissionStatus.Undetermined,
                                  requestPermission=lambda permission, callback: callbacks.append(callback))
        before = len(starts)
        with patch.object(speech_audio, 'QCoreApplication', SimpleNamespace(instance=lambda: pending)):
            capture.start()
            capture.cancel()
            callbacks[0](SimpleNamespace(status=lambda: speech_audio.Qt.PermissionStatus.Granted))
        check('a late OS permission grant cannot restart cancelled recording', len(starts) == before)

    class Handler(BaseHTTPRequestHandler):
        mode = 'success'
        received = []

        def do_POST(self):
            data = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            self.received.append((self.path, dict(self.headers), data))
            mode = self.mode
            if mode == 'slow':
                time.sleep(0.3)
            if mode == 'redirect':
                self.send_response(307)
                self.send_header('Location', f'http://127.0.0.1:{self.server.server_port}/leak')
                self.end_headers()
                return
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            body = (b'{"text":"' + b'x' * (MAX_RESPONSE_BYTES + 1) + b'"}' if mode == 'large'
                    else json.dumps({'text': 'Ajoute un fond de carte'}).encode())
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    address = f'http://127.0.0.1:{server.server_port}/v1'
    values = SpeechSettings(base_url=address, accepted_target=address, language='fr')
    panel = AgentPanel()
    panel.set_ready(True)
    panel.show()
    sent = []
    panel.send_requested.connect(sent.append)

    class Capture(QObject):
        level = 0.5

        def __init__(self, started, failed, limit, parent):
            super().__init__(parent)
            self.started, self.failed, self.limit = started, failed, limit
            self.cancelled = False

        def start(self, device):
            self.device = device
            self.started()

        def stop(self):
            return wav

        def cancel(self):
            self.cancelled = True

    voice = controller.AgentSpeechController(SimpleNamespace(panel=panel), capture_factory=Capture)
    panel.microphone_requested.connect(voice.toggle)
    panel.microphone_cancel_requested.connect(voice.cancel)

    def draft(text):
        panel.input.setText(text)
        cursor = panel.input.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        panel.input.setTextCursor(cursor)

    with patch.object(controller, 'load_speech_settings', return_value=values), \
            patch.object(controller, 'speech_key', return_value=''), \
            patch('tempfile.NamedTemporaryFile', side_effect=AssertionError('audio must stay in memory')), \
            patch('tempfile.mkstemp', side_effect=AssertionError('audio must stay in memory')):
        draft('Note 🌍')
        proxy = QNetworkProxy.applicationProxy()
        QNetworkProxy.setApplicationProxy(QNetworkProxy(QNetworkProxy.ProxyType.HttpProxy, '127.0.0.1', 9))
        try:
            panel.microphone_button.click()
            check('recording is visible and Enter cannot submit a partial dictation',
                  panel._speech_state == 'recording' and not panel.send_button.isEnabled()
                  and panel.speech_finish.isVisible() and panel.speech_finish.isEnabled())
            panel.input.returnPressed.emit()
            check('dictation never sends an agent request on Enter', not sent)
            panel.speech_finish.click()
            check('stop and transcribe opens a visible, cancellable transcription state',
                  panel._speech_state == 'transcribing' and panel.speech_progress.isVisible()
                  and not panel.speech_finish.isVisible() and panel.speech_cancel.isEnabled())
            until(lambda: panel._speech_state == 'idle')
        finally:
            QNetworkProxy.setApplicationProxy(proxy)
        check('local transcription bypasses the network proxy and preserves the existing draft',
              panel.input.text() == 'Note 🌍 Ajoute un fond de carte' and not sent)
        body = Handler.received[-1][2]
        check('the local service receives only WAV and transcription settings',
              b'RIFF' in body and b'name="language"\r\n\r\nfr' in body
              and Handler.received[-1][0] == '/v1/audio/transcriptions')
        panel.input.undo()
        check('inserting a transcript preserves input undo history', panel.input.text() == 'Note 🌍')

        Handler.mode = 'slow'
        before = len(Handler.received)
        panel.microphone_button.click()
        panel.microphone_button.click()
        until(lambda: len(Handler.received) > before)
        panel.input.escape_pressed.emit()
        check('Esc aborts transcription and retains the draft', panel._speech_state == 'idle' and panel.input.text() == 'Note 🌍')
        finished = []
        QTimer.singleShot(450, lambda: finished.append(True))
        until(lambda: bool(finished))
        check('a late transcription cannot insert text after cancellation', panel.input.text() == 'Note 🌍')
        panel.microphone_button.click()
        active = voice._capture
        panel.clear_thread()
        check('a new conversation cancels recording without uploading it', active.cancelled and panel._speech_state == 'idle')

        Handler.mode = 'redirect'
        before = len(Handler.received)
        panel.microphone_button.click()
        panel.microphone_button.click()
        until(lambda: panel._speech_state == 'idle')
        check('audio never follows a redirect', len(Handler.received) == before + 1 and 'redirect' in panel.status.text())

        Handler.mode = 'large'
        panel.microphone_button.click()
        panel.microphone_button.click()
        until(lambda: panel._speech_state == 'idle')
        check('oversized transcription responses are bounded and reported', 'too large' in panel.status.text())

        Handler.mode = 'slow'
        result = []
        speech_transport.SpeechRequest(transcription_request(values, wav),
            lambda text, error: result.append((text, error)), timeout_ms=20)
        until(lambda: bool(result))
        check('a total timeout releases the audio request', 'too long' in result[0][1])

    saved = []
    def save(settings, key, **kwargs):
        saved.append((settings, key))
        return settings
    dialog = SpeechSettingsDialog(SpeechSettings(), AgentSettings(), panel, saver=save)
    dialog.service.setCurrentIndex(dialog.service.findData('openai'))
    dialog.key.setText('private-key-for-test')
    dialog.accept()
    check('cloud audio needs an explicit destination choice before settings are saved', not saved)
    dialog.consent.setChecked(True)
    dialog.accept()
    check('local and cloud transcription are configurable independently of the chat provider',
          saved[0][0].service == 'openai' and saved[0][1] == 'private-key-for-test' and dialog.key.text() == '')
    dialog = SpeechSettingsDialog(values, AgentSettings(), panel, saver=save)
    dialog.address.setText('http://remote.example/v1')
    dialog.accept()
    check('a local service cannot silently send audio to a remote host', len(saved) == 1)
    dialog.reject()

    Handler.mode = 'success'
    before = len(Handler.received)
    dialog = SpeechSettingsDialog(SpeechSettings(), AgentSettings(), panel, saver=save, capture_factory=Capture)
    dialog.device.addItem('Test input', 'test-input')
    dialog.device.setCurrentIndex(dialog.device.findData('test-input'))
    dialog.show()
    dialog.test_microphone.click()
    check('microphone test uses the selected device and displays a live level without a service',
          dialog._test_capture.device == 'test-input' and dialog.test_level.value() == 50
          and len(Handler.received) == before and not dialog.test_transcription.isEnabled())
    dialog.test_microphone.click()
    check('stopping the microphone test retains a bounded in-memory recording without uploading',
          dialog._test_wav == wav and dialog.test_transcription.isEnabled()
          and len(Handler.received) == before)
    dialog.address.setText(address)
    dialog.model.setText('local-test-model')
    dialog.language.setText('fr')
    dialog.test_transcription.click()
    until(lambda: dialog._test_request is None)
    check('transcription tests unsaved settings and displays its result only in the dialog',
          dialog.test_result.toPlainText() == 'Ajoute un fond de carte' and len(saved) == 1
          and panel.input.text() == 'Note 🌍' and not sent
          and b'local-test-model' in Handler.received[-1][2] and b'\r\n\r\nfr' in Handler.received[-1][2])
    dialog.model.setText('corrected-model')
    check('editing test settings clears a previous success and allows retry with the same recording',
          dialog.test_result.isHidden() and dialog.test_result.toPlainText() == '' and bool(dialog._test_wav))
    Handler.mode = 'redirect'
    dialog.test_transcription.click()
    until(lambda: dialog._test_request is None)
    check('a failed transcription keeps the recording available for retry',
          'redirect' in dialog.test_status.text() and bool(dialog._test_wav)
          and dialog.test_transcription.isEnabled())
    Handler.mode = 'slow'
    dialog.test_transcription.click()
    pending = dialog._test_request
    dialog.address.setText(address + '/changed')
    check('editing the destination aborts any pending test upload', pending._over and dialog._test_request is None)
    dialog.test_transcription.click()
    pending = dialog._test_request
    dialog.test_microphone.click()
    check('a pending transcription test can be cancelled explicitly',
          pending._over and dialog._test_request is None and not dialog._test_wav)
    dialog.test_microphone.click()
    active = dialog._test_capture
    dialog._test_started -= 11
    dialog._test_tick()
    check('microphone tests stop automatically after ten seconds without uploading',
          dialog._test_capture is None and bool(dialog._test_wav) and not active.cancelled)
    dialog.test_microphone.click()
    active = dialog._test_capture
    late_started = active.started
    dialog.reject()
    late_started()
    check('closing settings releases the microphone, recording and delayed permission callbacks',
          active.cancelled and not dialog._test_wav and not dialog._test_timer.isActive())

    dialog = SpeechSettingsDialog(SpeechSettings(), AgentSettings(), panel, saver=save, capture_factory=Capture)
    dialog.test_microphone.click()
    dialog.test_microphone.click()
    dialog.service.setCurrentIndex(dialog.service.findData('openai'))
    before = len(Handler.received)
    dialog.test_transcription.click()
    check('cloud test audio cannot be uploaded without explicit consent',
          'Choose whether' in dialog.test_status.text() and len(Handler.received) == before)
    dialog.consent.setChecked(True)
    dialog.test_transcription.click()
    check('cloud tests report missing credentials without saving the form or uploading',
          'API key' in dialog.test_status.text() and len(Handler.received) == before and len(saved) == 1)
    dialog.reject()

    class TestRequest:
        def __init__(self, request, callback, parent):
            self.request, self.callback, self.aborted = request, callback, False

        def abort(self):
            self.aborted = True

    from filter_mate.adapters.agent import speech_settings
    for service, model, language_field in (('openai', 'gpt-transcribe', 'languages[]'),
                                           ('mistral', 'voxtral-mini-transcribe-3', 'language')):
        dialog = SpeechSettingsDialog(SpeechSettings(), AgentSettings(), panel, saver=save,
                                      capture_factory=Capture, request_factory=TestRequest)
        dialog.service.setCurrentIndex(dialog.service.findData(service))
        check(service + ' selects its own transcription address and model',
              dialog.address.text() == SERVICES[service][0] and dialog.model.text() == model)
        dialog.language.setText('fr')
        dialog.key.setText(service + '-test-secret')
        dialog.test_microphone.click()
        dialog.test_microphone.click()
        dialog.test_transcription.click()
        check(service + ' microphone tests remain local until cloud consent is given',
              dialog._test_request is None and 'Choose whether' in dialog.test_status.text())
        dialog.consent.setChecked(True)
        dialog.test_transcription.click()
        pending = dialog._test_request
        check(service + ' transcription tests use the correct model, language format and unsaved key',
              pending.request.url == SERVICES[service][0] + '/audio/transcriptions'
              and pending.request.headers['Authorization'] == 'Bearer ' + service + '-test-secret'
              and f'name="{language_field}"\r\n\r\nfr'.encode() in pending.request.body
              and model.encode() in pending.request.body)
        pending.callback('Texte reconnu par ' + service, '')
        check(service + ' shows the test transcript without saving or sending a chat request',
              dialog.test_result.toPlainText() == 'Texte reconnu par ' + service and len(saved) == 1 and not sent)
        dialog.test_transcription.click()
        pending = dialog._test_request
        next_service = 'mistral' if service == 'openai' else 'openai'
        dialog.service.setCurrentIndex(dialog.service.findData(next_service))
        check(service + ' credentials and consent are cleared when changing provider during a test',
              pending.aborted and dialog._test_request is None and not dialog.key.text()
              and not dialog.consent.isChecked() and not dialog.reuse_key.isChecked()
              and dialog.test_result.toPlainText() == '' and bool(dialog._test_wav))
        dialog.reject()

        provider = AgentSettings(preset=service, authcfg='chat-auth', key_target=SERVICES[service][0])
        preferences = SpeechSettings(service=service, accepted_target=SERVICES[service][0])
        dialog = SpeechSettingsDialog(preferences, provider, panel, saver=save,
                                      capture_factory=Capture, request_factory=TestRequest)
        dialog.reuse_key.setChecked(True)
        dialog.test_microphone.click()
        dialog.test_microphone.click()
        with patch.object(speech_settings, 'load_settings', return_value=provider), \
                patch.object(speech_settings, 'read_key', return_value='chat-secret') as read_key:
            dialog.test_transcription.click()
            pending = dialog._test_request
            check(service + ' can test transcription using the matching chat provider key',
                  pending.request.headers['Authorization'] == 'Bearer chat-secret'
                  and read_key.call_args.args == ('chat-auth',) and not dialog.key.isEnabled())
        dialog.reject()

    secured = SpeechSettings(service='openai', accepted_target='https://api.openai.com/v1',
                             authcfg='saved-auth', key_target='https://api.openai.com/v1')
    dialog = SpeechSettingsDialog(secured, AgentSettings(), panel, saver=save,
                                  capture_factory=Capture, request_factory=TestRequest)
    dialog.test_microphone.click()
    dialog.test_microphone.click()
    with patch.object(speech_settings, 'read_key', return_value='stored-secret') as read_key:
        dialog.test_transcription.click()
        pending = dialog._test_request
        check('transcription tests can use a stored key belonging to the same address',
              pending.request.headers['Authorization'] == 'Bearer stored-secret'
              and read_key.call_args.args == ('saved-auth',))
    dialog.key.setText('unsaved-secret')
    with patch.object(speech_settings, 'read_key', side_effect=AssertionError('must use the entered key')):
        dialog.test_transcription.click()
    pending = dialog._test_request
    check('an entered test key overrides the stored credential without saving it',
          pending.request.headers['Authorization'] == 'Bearer unsaved-secret' and len(saved) == 1)
    dialog.reject()
    pending.callback('late result', '')
    check('closing settings aborts a pending upload and ignores a late response',
          pending.aborted and not dialog._test_wav and dialog.test_result.toPlainText() == '')

    class MissingMicrophone(Capture):
        def start(self, device):
            raise ValueError('No microphone is available. Check the device in Microphone settings.')

    dialog = SpeechSettingsDialog(values, AgentSettings(), panel, saver=save, capture_factory=MissingMicrophone)
    dialog.test_microphone.click()
    check('a missing microphone is reported in the settings dialog without enabling transcription',
          'No microphone' in dialog.test_status.text() and dialog._test_capture is None
          and not dialog.test_transcription.isEnabled())
    dialog.reject()

    from qgis.PyQt.QtCore import QTranslator
    translator = QTranslator()
    check('the French speech catalog loads', translator.load('/src/i18n/FilterMate_fr.qm'))
    app.installTranslator(translator)
    panel.set_speech_state('recording', 'test')
    check('microphone controls are translated in French', panel.microphone_button.toolTip() == 'Arrêter l’enregistrement et transcrire')
    voice._fail('No speech was recognized. Try recording again.')
    check('speech errors are translated without being interpreted as rich text',
          'Aucune parole reconnue' in panel.status.text())
    dialog = SpeechSettingsDialog(values, AgentSettings(), panel, saver=save)
    check('microphone test controls are translated in French',
          dialog.test_microphone.text() == 'Tester le microphone' and
          dialog.test_transcription.text() == 'Tester la transcription')
    dialog.reject()
    app.removeTranslator(translator)

    voice.close()
    panel.close()
    server.shutdown()
    server.server_close()
    print('All agent speech checks passed', flush=True)


try:
    main()
except Exception:
    traceback.print_exc()
    os._exit(1)
os._exit(0)
