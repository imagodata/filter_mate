# -*- coding: utf-8 -*-
"""Qt5/Qt6 microphone capture without audio files. Multimedia is imported only when used."""
import sys
import importlib

from qgis.PyQt.QtCore import QCoreApplication, QObject, QTimer, Qt

from ...core.agent.speech import PcmBuffer


def _multimedia():
    try:
        from qgis.PyQt import QtMultimedia
        return QtMultimedia
    except ImportError:
        # Older QGIS does not wrap Multimedia even when the matching PyQt component is installed.
        from qgis.PyQt.QtCore import QT_VERSION_STR
        return importlib.import_module(('PyQt6' if QT_VERSION_STR.startswith('6.') else 'PyQt5') + '.QtMultimedia')


def _devices():
    media = _multimedia()
    if hasattr(media, 'QMediaDevices'):
        return media, list(media.QMediaDevices.audioInputs()), media.QMediaDevices.defaultAudioInput(), True
    mode = getattr(getattr(media.QAudio, 'Mode', media.QAudio), 'AudioInput')
    return media, list(media.QAudioDeviceInfo.availableDevices(mode)), media.QAudioDeviceInfo.defaultInputDevice(), False


def device_choices():
    _media, devices, _default, qt6 = _devices()
    return [(('qt6:' + bytes(device.id()).hex(), device.description()) if qt6 else
             ('qt5:' + device.deviceName(), device.deviceName())) for device in devices]


class AudioCapture(QObject):
    def __init__(self, on_started, on_error, on_limit, parent=None):
        super().__init__(parent)
        self.on_started, self.on_error, self.on_limit = on_started, on_error, on_limit
        self._source = self._io = self.buffer = None
        self._token = 0
        self._limit_queued = False

    def start(self, device_id=''):
        self._token += 1
        token = self._token
        try:
            from qgis.PyQt.QtCore import QMicrophonePermission
        except ImportError:
            self._begin(device_id)
            return
        app = QCoreApplication.instance()
        if not hasattr(app, 'checkPermission'):
            self._begin(device_id)
            return
        permission = QMicrophonePermission()
        status = app.checkPermission(permission)
        if status == Qt.PermissionStatus.Granted:
            self._begin(device_id)
        elif status == Qt.PermissionStatus.Denied:
            raise ValueError('Microphone access was denied. Enable it in system privacy settings.')
        else:
            def answered(result):
                if token != self._token:
                    return
                try:
                    if result.status() != Qt.PermissionStatus.Granted:
                        raise ValueError('Microphone access was denied. Enable it in system privacy settings.')
                    self._begin(device_id)
                except Exception as exc:
                    self.on_error(str(exc))
            app.requestPermission(permission, answered)

    def _begin(self, device_id):
        try:
            media, devices, selected, qt6 = _devices()
        except ImportError:
            raise ValueError('Qt Multimedia is unavailable in this QGIS installation.') from None
        if device_id:
            selected = next((device for device in devices if
                ('qt6:' + bytes(device.id()).hex() if qt6 else 'qt5:' + device.deviceName()) == device_id), None)
        if selected is None or selected.isNull():
            raise ValueError('No microphone is available. Check the device in Microphone settings.')
        audio_format = media.QAudioFormat()
        audio_format.setSampleRate(16000)
        audio_format.setChannelCount(1)
        if qt6:
            audio_format.setSampleFormat(media.QAudioFormat.SampleFormat.Int16)
        else:
            audio_format.setCodec('audio/pcm')
            audio_format.setSampleSize(16)
            audio_format.setSampleType(media.QAudioFormat.SampleType.SignedInt)
            audio_format.setByteOrder(media.QAudioFormat.Endian.LittleEndian)
        if not selected.isFormatSupported(audio_format):
            audio_format = selected.preferredFormat() if qt6 else selected.nearestFormat(audio_format)
        if qt6:
            scope = media.QAudioFormat.SampleFormat
            sample_format = {scope.UInt8: 'u8', scope.Int16: 's16', scope.Int32: 's32', scope.Float: 'f32'}.get(
                audio_format.sampleFormat(), '')
            little = sys.byteorder == 'little'
            source_type = media.QAudioSource
        else:
            scope = media.QAudioFormat.SampleType
            sample_format = {(scope.SignedInt, 16): 's16', (scope.SignedInt, 32): 's32',
                             (scope.UnSignedInt, 8): 'u8', (scope.Float, 32): 'f32'}.get(
                (audio_format.sampleType(), audio_format.sampleSize()), '')
            little = audio_format.byteOrder() == media.QAudioFormat.Endian.LittleEndian
            source_type = media.QAudioInput
        self.buffer = PcmBuffer(audio_format.sampleRate(), audio_format.channelCount(), sample_format, little)
        self._source = source_type(selected, audio_format, self)
        self._source.stateChanged.connect(self._state_changed)
        self._io = self._source.start()
        if self._io is None:
            self.cancel()
            raise ValueError('The microphone could not be started. Check permissions and audio input settings.')
        self._io.readyRead.connect(self._read)
        self.on_started()

    def _state_changed(self, *_):
        if self._source is not None and int(self._source.error().value if hasattr(self._source.error(), 'value')
                                            else self._source.error()) != 0:
            self.on_error('The microphone stopped unexpectedly. Check the selected input device.')

    def _read(self):
        if self._io is None or self.buffer is None:
            return
        try:
            self.buffer.feed(bytes(self._io.readAll()))
            if self.buffer.full and not self._limit_queued:
                self._limit_queued = True
                token = self._token
                QTimer.singleShot(0, lambda: self.on_limit() if token == self._token else None)
        except Exception as exc:
            self.on_error(str(exc))  # no exception may escape a Qt audio slot

    def stop(self):
        self._read()
        buffer = self.buffer
        self._release()
        if buffer is None:
            raise ValueError('No audio was recorded. Check the microphone and try again.')
        try:
            return buffer.wav()
        finally:
            buffer.clear()

    def _release(self):
        self._token += 1
        source, io = self._source, self._io
        self._source = self._io = None
        self._limit_queued = False
        if io is not None:
            try:
                io.readyRead.disconnect(self._read)
            except (TypeError, RuntimeError):
                pass
        if source is not None:
            source.stop()
            source.deleteLater()
        self.buffer = None

    def cancel(self):
        buffer = self.buffer
        self._release()
        if buffer is not None:
            buffer.clear()
