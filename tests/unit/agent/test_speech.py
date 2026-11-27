"""Dictation's data boundary: bounded PCM, no files, explicit destination, no automatic submission."""
import io
import struct
import wave
from dataclasses import replace

import pytest

from core.agent.speech import PcmBuffer, SpeechSettings, transcription_request, transcription_text, validate_settings

pytestmark = pytest.mark.unit


def local(**kwargs):
    values = SpeechSettings(**kwargs)
    return replace(values, accepted_target=values.target)


def recorded():
    buffer = PcmBuffer(16000, 1, 's16')
    buffer.feed(struct.pack('<h', 2000) * 4000)
    return buffer.wav()


def test_pcm_wav_and_incomplete_frames_are_independent_of_chunk_boundaries():
    raw = b''.join(struct.pack('<hh', index * 3, index) for index in range(10000))
    whole, chunks = PcmBuffer(44100, 2, 's16'), PcmBuffer(44100, 2, 's16')
    whole.feed(raw)
    for offset in range(0, len(raw), 173):
        chunks.feed(raw[offset:offset + 173])
    assert whole.wav() == chunks.wav()
    with wave.open(io.BytesIO(chunks.wav())) as stream:
        assert (stream.getnchannels(), stream.getsampwidth(), stream.getframerate()) == (1, 2, 16000)
        assert abs(stream.getnframes() - 10000 * 16000 / 44100) <= 1


@pytest.mark.parametrize('sample_format, data', [
    ('s16', struct.pack('<h', 1200)), ('s32', struct.pack('<i', 1200 * 65536)),
    ('f32', struct.pack('<f', 1200 / 32768)), ('u8', bytes([133]))])
def test_common_device_formats_are_normalized(sample_format, data):
    buffer = PcmBuffer(48000, 1, sample_format)
    buffer.feed(data * 10000)
    with wave.open(io.BytesIO(buffer.wav())) as stream:
        assert stream.getnframes() > 3000
        assert struct.unpack('<h', stream.readframes(1))[0] > 1000


def test_big_endian_and_duration_limit_are_bounded():
    buffer = PcmBuffer(16000, 1, 's16', little_endian=False, max_samples=2500)
    buffer.feed(struct.pack('>h', 4000) * 10000)
    assert buffer.full and buffer.seconds == 2500 / 16000
    with wave.open(io.BytesIO(buffer.wav())) as stream:
        assert stream.getnframes() == 2500
        assert struct.unpack('<h', stream.readframes(1))[0] == 4000
    buffer.clear()
    assert buffer.seconds == 0


def test_silence_and_short_recordings_are_never_submitted():
    for data in (b'', b'\0\0' * 4000, struct.pack('<h', 2000) * 10):
        buffer = PcmBuffer(16000, 1, 's16')
        buffer.feed(data)
        with pytest.raises(ValueError, match='No audio'):
            buffer.wav()


def test_live_level_drops_with_silence_without_losing_the_recording_peak():
    buffer = PcmBuffer(16000, 1, 's16')
    buffer.feed(struct.pack('<h', 16384) * 4000)
    assert buffer.level == 0.5
    buffer.feed(b'\0\0' * 4000)
    assert buffer.level == 0
    assert len(buffer.wav()) > 44
    buffer.clear()
    assert buffer.level == 0


def test_local_multipart_contains_only_audio_model_and_language():
    request = transcription_request(local(language='fr'), recorded())
    assert request.url == 'http://127.0.0.1:8000/v1/audio/transcriptions'
    assert 'Authorization' not in request.headers
    assert b'name="file"; filename="dictation.wav"' in request.body and b'RIFF' in request.body
    assert b'name="model"\r\n\r\nwhisper-1' in request.body
    assert b'name="language"\r\n\r\nfr' in request.body
    assert 'RIFF' not in repr(request)


def test_cloud_key_stays_out_of_repr_and_requires_exact_configuration():
    values = SpeechSettings(service='openai')
    with pytest.raises(ValueError, match='Configure'):
        transcription_request(values, recorded(), 'secret')
    values = replace(values, accepted_target=values.target)
    with pytest.raises(ValueError, match='API key'):
        transcription_request(values, recorded())
    request = transcription_request(values, recorded(), 'private-key')
    assert request.headers['Authorization'] == 'Bearer private-key'
    assert 'private-key' not in repr(request)
    assert b'gpt-transcribe' in request.body
    with pytest.raises(ValueError, match='Configure'):
        transcription_request(replace(values, base_url='https://another.example/v1'), recorded(), 'private-key')


@pytest.mark.parametrize('service, model, language_field', [
    ('openai', 'gpt-transcribe', 'languages[]'),
    ('openai', 'whisper-1', 'language'),
    ('mistral', 'voxtral-mini-transcribe-3', 'language'),
    ('local', 'custom-whisper', 'language'),
])
def test_transcription_wire_format_matches_each_provider(service, model, language_field):
    settings = local(service=service, model=model, language='fr')
    key = '' if service == 'local' else 'provider-secret'
    request = transcription_request(settings, recorded(), key)
    assert request.url == settings.target + '/audio/transcriptions'
    assert f'name="model"\r\n\r\n{model}\r\n'.encode() in request.body
    assert f'name="{language_field}"\r\n\r\nfr\r\n'.encode() in request.body
    other_field = 'language' if language_field == 'languages[]' else 'languages[]'
    assert f'name="{other_field}"'.encode() not in request.body
    if key:
        assert request.headers['Authorization'] == 'Bearer ' + key
    else:
        assert 'Authorization' not in request.headers


@pytest.mark.parametrize('service', ['openai', 'mistral', 'local'])
def test_automatic_language_is_omitted_for_every_provider(service):
    request = transcription_request(local(service=service), recorded(), 'provider-secret')
    assert b'name="language"' not in request.body and b'name="languages[]"' not in request.body


def test_provider_language_requirements_are_validated_before_upload():
    validate_settings(local(service='openai', language='zh-tw'))
    validate_settings(local(service='openai', language='eng'))
    validate_settings(local(service='mistral', language='fr'))
    for language in ('eng', 'zh-tw'):
        with pytest.raises(ValueError, match='Mistral requires a two-letter'):
            transcription_request(local(service='mistral', language=language), recorded(), 'provider-secret')
    with pytest.raises(ValueError, match='Language is an ISO code'):
        validate_settings(local(service='openai', model='whisper-1', language='zh-tw'))


@pytest.mark.parametrize('values', [
    SpeechSettings(base_url='http://remote.example/v1'), SpeechSettings(base_url='file:///tmp/audio'),
    SpeechSettings(base_url='http://user:pass@localhost/v1'), SpeechSettings(base_url='http://localhost/v1?token=x'),
    SpeechSettings(service='openai', base_url='http://remote.example/v1'), SpeechSettings(language='fr-FR'),
    SpeechSettings(model='bad\r\nname'), SpeechSettings(service='unknown')])
def test_invalid_targets_and_fields_are_refused(values):
    with pytest.raises(ValueError):
        validate_settings(values)


def test_transcript_is_plain_text_and_response_is_bounded():
    assert transcription_text(b'{"text":"  <layer> filtre  ","extra":42}') == '<layer> filtre'
    for body in (b'not json', b'{"text":" "}', b'{"text":false}', b'[]', b'{' * 300000):
        with pytest.raises(ValueError):
            transcription_text(body)
