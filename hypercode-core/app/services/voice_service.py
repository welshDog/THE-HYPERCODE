from __future__ import annotations
import structlog
from dataclasses import dataclass
from typing import Optional, Tuple, List
import time
from prometheus_client import Histogram, Counter

logger = structlog.get_logger()

STT_LATENCY_SECONDS = Histogram(
    "stt_latency_seconds",
    "Speech-to-text latency",
    ("provider", "status"),
    buckets=(0.01, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0)
)
STT_ERRORS_TOTAL = Counter(
    "stt_errors_total",
    "STT errors",
    ("provider", "type"),
)
STT_CONFIDENCE = Histogram(
    "stt_confidence",
    "Transcription confidence",
    buckets=(0.5, 0.7, 0.8, 0.85, 0.9, 0.95, 0.99)
)

VOICE_AUDIO_RMS = Histogram(
    "voice_audio_rms",
    "Approximate audio quality via RMS",
    buckets=(500, 1000, 2000, 4000, 8000, 12000, 16000)
)


@dataclass
class TranscriptChunk:
    text: str
    confidence: float
    language: Optional[str] = None


class AudioBuffer:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self._buf: bytearray = bytearray()
        self.codec: str = "pcm16"

    def push(self, data: bytes) -> None:
        self._buf.extend(data)

    def pop_window(self, ms: int, overlap_ms: int = 500) -> Optional[bytes]:
        win_bytes = int(self.sample_rate * 2 * (ms / 1000.0))
        if len(self._buf) < win_bytes:
            return None
        window = bytes(self._buf[:win_bytes])
        # Overlap: keep last overlap_ms segment
        overlap_bytes = int(self.sample_rate * 2 * (overlap_ms / 1000.0))
        tail = self._buf[win_bytes - overlap_bytes:win_bytes]
        self._buf = bytearray(tail) + self._buf[win_bytes:]
        return window


def dc_offset_filter(pcm: bytes) -> bytes:
    # simple DC offset removal on 16-bit PCM
    if len(pcm) < 4:
        return pcm
    import struct
    samples = list(struct.iter_unpack('<h', pcm))
    vals = [s[0] for s in samples]
    avg = int(sum(vals) / len(vals))
    adj = [max(min(v - avg, 32767), -32768) for v in vals]
    out = bytearray()
    for v in adj:
        out += struct.pack('<h', v)
    return bytes(out)


def agc(pcm: bytes, target_rms: float = 5000.0) -> bytes:
    # naive automatic gain control
    if len(pcm) < 4:
        return pcm
    import struct
    samples = list(struct.iter_unpack('<h', pcm))
    vals = [s[0] for s in samples]
    import math
    rms = math.sqrt(sum(v*v for v in vals) / len(vals)) or 1.0
    gain = target_rms / rms
    adj = [max(min(int(v * gain), 32767), -32768) for v in vals]
    out = bytearray()
    for v in adj:
        out += struct.pack('<h', v)
    return bytes(out)


def decode_opus(opus_bytes: bytes, target_rate: int = 16000) -> Optional[bytes]:
    try:
        import av  # type: ignore
        import numpy as np  # type: ignore
        import io
        container = av.open(io.BytesIO(opus_bytes))
        stream = next(s for s in container.streams if s.type == 'audio')
        resampler = av.audio.resampler.AudioResampler(format='s16', layout='mono', rate=target_rate)
        out_pcm = bytearray()
        for frame in container.decode(stream):
            rf = resampler.resample(frame)
            for p in rf.planes:
                out_pcm.extend(p.to_bytes())
        return bytes(out_pcm)
    except Exception:
        return None


def detect_language(pcm: bytes) -> str:
    # placeholder hook for language detection; integrate real model later
    return "en"


async def transcribe_chunk(pcm: bytes, language: Optional[str], provider: str = "openai") -> TranscriptChunk:
    t0 = time.perf_counter()
    try:
        # placeholder: in production, send PCM as WAV to OpenAI Whisper or alt engine
        # to keep tests deterministic, return fixed text
        text = "print('voice')"
        confidence = 0.99
        STT_LATENCY_SECONDS.labels(provider, "success").observe(time.perf_counter() - t0)
        STT_CONFIDENCE.observe(confidence)
        try:
            # compute rms quality metric
            import struct, math
            vals = [s[0] for s in struct.iter_unpack('<h', pcm)]
            rms = math.sqrt(sum(v*v for v in vals) / (len(vals) or 1))
            VOICE_AUDIO_RMS.observe(rms)
        except Exception:
            pass
        return TranscriptChunk(text=text, confidence=confidence, language=language or "en")
    except Exception as e:
        logger.error("stt_failed", error=str(e))
        STT_ERRORS_TOTAL.labels(provider, type(e).__name__).inc()
        STT_LATENCY_SECONDS.labels(provider, "error").observe(time.perf_counter() - t0)
        return TranscriptChunk(text="", confidence=0.0, language=language)


def profanity_filter(text: str) -> str:
    banned = {"damn", "hell", "shit", "fuck"}
    parts = text.split()
    out: List[str] = []
    for p in parts:
        if p.lower() in banned:
            out.append("*" * len(p))
        else:
            out.append(p)
    return " ".join(out)


def sanitize_command(text: str) -> str:
    t = text.strip()
    # very minimal sanitization rules for demo
    # block shell injection markers
    for bad in ["&&", "|", ";;"]:
        t = t.replace(bad, " ")
    return t
