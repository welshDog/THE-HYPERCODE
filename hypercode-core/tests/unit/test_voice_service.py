import struct
import pytest
from app.services.voice_service import AudioBuffer, dc_offset_filter, agc, transcribe_chunk


def gen_pcm(samples):
    b = bytearray()
    for v in samples:
        b += struct.pack('<h', v)
    return bytes(b)


def test_dc_offset_filter_reduces_offset():
    pcm = gen_pcm([1000] * 160)
    out = dc_offset_filter(pcm)
    vals = [s[0] for s in struct.iter_unpack('<h', out)]
    assert abs(sum(vals) / len(vals)) < 10


def test_agc_scales_signal():
    pcm = gen_pcm([100] * 160)
    out = agc(pcm, target_rms=5000)
    vals = [s[0] for s in struct.iter_unpack('<h', out)]
    import math
    rms = math.sqrt(sum(v*v for v in vals) / len(vals))
    assert rms > 1000


@pytest.mark.asyncio
async def test_audio_buffer_window_and_transcribe():
    buf = AudioBuffer(sample_rate=16000)
    # push 1s worth of zeros
    buf.push(bytes(16000 * 2))
    win = buf.pop_window(ms=1000, overlap_ms=500)
    assert win is not None
    tr = await transcribe_chunk(win, language="en")
    assert tr.text
    assert tr.confidence > 0.9

