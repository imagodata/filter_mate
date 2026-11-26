# -*- coding: utf-8 -*-
"""Bounded in-memory dictation: PCM conversion and the OpenAI-compatible transcription wire format."""
from __future__ import annotations

import io
import ipaddress
import json
import math
import re
import struct
import uuid
import wave
from dataclasses import dataclass
from urllib.parse import urlsplit

from .providers.base import HttpRequest, check_base_url

SAMPLE_RATE = 16000
MAX_SECONDS = 120
MAX_SAMPLES = SAMPLE_RATE * MAX_SECONDS
MAX_WAV_BYTES = MAX_SAMPLES * 2 + 44
MAX_RESPONSE_BYTES = 256 * 1024
SERVICES = {
    'local': ('http://127.0.0.1:8000/v1', 'whisper-1'),
    'openai': ('https://api.openai.com/v1', 'gpt-transcribe'),
    'mistral': ('https://api.mistral.ai/v1', 'voxtral-mini-latest'),
}


@dataclass(frozen=True)
class SpeechSettings:
    service: str = 'local'
    base_url: str = ''
    model: str = ''
    language: str = ''
    device: str = ''
    authcfg: str = ''
    key_target: str = ''
    accepted_target: str = ''
    use_provider_key: bool = False

    @property
    def target(self):
        return (self.base_url.strip() or SERVICES.get(self.service, SERVICES['local'])[0]).rstrip('/')

    @property
    def chosen_model(self):
        return self.model.strip() or SERVICES.get(self.service, SERVICES['local'])[1]

    @property
    def configured(self):
        return self.accepted_target == self.target


def validate_settings(settings: SpeechSettings):
    if settings.service not in SERVICES:
        raise ValueError('Choose a transcription service.')
    target = settings.target
    check_base_url(target, settings.service != 'local')
    parts = urlsplit(target)
    if parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError('Use a service address without credentials, query or fragment.')
    if settings.service == 'local':
        host = (parts.hostname or '').lower()
        try:
            local = host == 'localhost' or ipaddress.ip_address(host).is_loopback
        except ValueError:
            local = host == 'localhost'
        if not local:
            raise ValueError('The local transcription service must run on this computer (localhost).')
    if not settings.chosen_model or len(settings.chosen_model) > 200 or any(c in settings.chosen_model for c in '\r\n'):
        raise ValueError('Choose a transcription model (at most 200 characters).')
    if settings.language and not re.fullmatch(r'[a-z]{2,3}', settings.language):
        raise ValueError('Language is an ISO code such as fr or en, or empty for automatic detection.')


def transcription_request(settings: SpeechSettings, wav: bytes, key: str = '') -> HttpRequest:
    validate_settings(settings)
    if not settings.configured:
        raise ValueError('Configure the microphone service before recording.')
    if settings.service != 'local' and not key:
        raise ValueError('This transcription service needs an API key.')
    if not 44 < len(wav) <= MAX_WAV_BYTES or not wav.startswith(b'RIFF') or wav[8:12] != b'WAVE':
        raise ValueError('The recorded audio is empty or exceeds the dictation limit.')
    if '\r' in key or '\n' in key:
        raise ValueError('The API key contains an invalid character.')
    check_base_url(settings.target, key)
    boundary = 'filtermate-' + uuid.uuid4().hex
    parts = []
    fields = {'model': settings.chosen_model}
    if settings.language:
        # The current OpenAI model takes a list of language hints; legacy/compatible servers use language.
        fields['languages[]' if settings.service == 'openai' and settings.chosen_model == 'gpt-transcribe'
               else 'language'] = settings.language
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    parts.extend([f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="dictation.wav"\r\n'
                  'Content-Type: audio/wav\r\n\r\n'.encode(), wav, f'\r\n--{boundary}--\r\n'.encode()])
    headers = {'Content-Type': f'multipart/form-data; boundary={boundary}', 'Accept': 'application/json'}
    if key:
        headers['Authorization'] = 'Bearer ' + key
    return HttpRequest(settings.target + '/audio/transcriptions', headers, b''.join(parts))


def transcription_text(body: bytes) -> str:
    if len(body) > MAX_RESPONSE_BYTES:
        raise ValueError('The transcription response is too large.')
    try:
        data = json.loads(body)
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError('The transcription service did not return a JSON transcript.') from None
    text = data.get('text') if isinstance(data, dict) else None
    if not isinstance(text, str) or not text.strip():
        raise ValueError('No speech was recognized. Try recording again.')
    if len(text) > 20000:
        raise ValueError('The transcript is too long for a dictation.')
    return text.strip()


class PcmBuffer:
    """Convert device PCM in small chunks to mono 16-bit/16 kHz, with a bounded recording duration.

    No audioop (removed in Python 3.13), external encoder, temporary file or model download is needed.
    Fractional resampling position and incomplete device frames survive chunk boundaries.
    """
    def __init__(self, rate: int, channels: int, sample_format: str, little_endian=True, max_samples=MAX_SAMPLES):
        codes = {'s16': ('h', 32768), 's32': ('i', 2147483648), 'u8': ('B', 128), 'f32': ('f', 1)}
        if sample_format not in codes or not 8000 <= rate <= 192000 or not 1 <= channels <= 8:
            raise ValueError('The microphone audio format is not supported.')
        code, self._scale = codes[sample_format]
        self._unsigned = sample_format == 'u8'
        self._frame = struct.Struct(('<' if little_endian else '>') + code * channels)
        self._rate, self._channels = rate, channels
        self._carry = b''
        self._pcm = bytearray()
        self._index, self._next, self._previous = 0, 0, None
        self._max = min(MAX_SAMPLES, max_samples)
        self.peak = 0

    @property
    def full(self):
        return len(self._pcm) // 2 >= self._max

    @property
    def seconds(self):
        return len(self._pcm) / (2 * SAMPLE_RATE)

    def feed(self, chunk: bytes):
        chunk = self._carry + chunk
        end = len(chunk) - len(chunk) % self._frame.size
        self._carry = chunk[end:]
        for frame in self._frame.iter_unpack(chunk[:end]):
            if self.full:
                break
            value = sum(frame) / self._channels
            if self._unsigned:
                value -= 128
            value = value * 32768 / self._scale
            if not math.isfinite(value):
                value = 0
            if self._previous is None:
                self._previous = value
            while self._next <= self._index * SAMPLE_RATE and not self.full:
                fraction = (self._next - (self._index - 1) * SAMPLE_RATE) / SAMPLE_RATE
                interpolated = self._previous + min(1, max(0, fraction)) * (value - self._previous)
                sample = max(-32768, min(32767, round(interpolated)))
                self.peak = max(self.peak, abs(sample))
                self._pcm.extend(struct.pack('<h', sample))
                self._next += self._rate
            self._previous = value
            self._index += 1

    def wav(self):
        if self.seconds < 0.15 or not self.peak:
            raise ValueError('No audio was recorded. Check the microphone and try again.')
        output = io.BytesIO()
        with wave.open(output, 'wb') as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(SAMPLE_RATE)
            stream.writeframes(self._pcm)
        return output.getvalue()

    def clear(self):
        self._pcm.clear()
        self._carry = b''
