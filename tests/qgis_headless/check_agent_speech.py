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
    from filter_mate.core.agent.speech import MAX_RESPONSE_BYTES, SpeechSettings, transcription_request
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
        def __init__(self, started, failed, limit, parent):
            super().__init__(parent)
            self.started, self.failed, self.limit = started, failed, limit
            self.cancelled = False

        def start(self, device):
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
                  panel._speech_state == 'recording' and not panel.send_button.isEnabled())
            panel.input.returnPressed.emit()
            check('dictation never sends an agent request on Enter', not sent)
            panel.microphone_button.click()
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

    from qgis.PyQt.QtCore import QTranslator
    translator = QTranslator()
    check('the French speech catalog loads', translator.load('/src/i18n/FilterMate_fr.qm'))
    app.installTranslator(translator)
    panel.set_speech_state('recording', 'test')
    check('microphone controls are translated in French', panel.microphone_button.toolTip() == 'Arrêter l’enregistrement et transcrire')
    voice._fail('No speech was recognized. Try recording again.')
    check('speech errors are translated without being interpreted as rich text',
          'Aucune parole reconnue' in panel.status.text())
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
