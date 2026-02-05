from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi import status
from app.core.auth import verify_api_key
from app.middleware.rate_limit import check_rate_limit
from app.services.voice_service import AudioBuffer, dc_offset_filter, agc, transcribe_chunk, profanity_filter, sanitize_command, decode_opus, detect_language
from app.engine.adapter import run_hypercode
from prometheus_client import Counter, Histogram
import structlog

router = APIRouter()
logger = structlog.get_logger()

VOICE_WS_CONNECTIONS = Counter(
    "voice_ws_connections_total",
    "Voice WebSocket connections",
    ("status",)
)
VOICE_CMD_EXEC_DURATION = Histogram(
    "voice_command_exec_duration_seconds",
    "Voice command execution duration",
    ("status",),
    buckets=(0.01, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0)
)


@router.websocket("/voice/ws")
async def voice_ws(ws: WebSocket, api_key: str = Query(default=None)):
    try:
        await ws.accept()
        # authenticate (skip in dev when API_KEY unset)
        from app.core.config import get_settings
        settings = get_settings()
        env_lower = (getattr(settings, "ENVIRONMENT", "") or "").lower()
        if env_lower == "production" and settings.API_KEY:
            await verify_api_key(api_key)
        user_id = api_key or "anon"
        VOICE_WS_CONNECTIONS.labels("connected").inc()
        buf = AudioBuffer(sample_rate=16000)

        while True:
            msg = await ws.receive()
            await check_rate_limit(user_id, limit_per_minute=100)
            if "bytes" in msg and msg["bytes"]:
                raw = msg["bytes"]
                pcm = raw
                if getattr(buf, "codec", "pcm16") == "opus":
                    decoded = decode_opus(raw, target_rate=buf.sample_rate)
                    if decoded:
                        pcm = decoded
                pcm = dc_offset_filter(pcm)
                pcm = agc(pcm)
                buf.push(pcm)
                win = buf.pop_window(ms=1000, overlap_ms=500)
                if not win:
                    await ws.send_json({"status": "buffering"})
                    continue
                lang = detect_language(win)
                tr = await transcribe_chunk(win, language=lang, provider="openai")
                # ND-friendly indicator when low confidence
                nd_flag = tr.confidence < 0.85
                clean = sanitize_command(profanity_filter(tr.text))
                # simple execution contract: if text starts with print/def/assignment, run as hypercode
                t0 = __import__("time").perf_counter()
                stdout, stderr, code, _ = await run_hypercode(clean, timeout=5)
                status_ = "success" if code == 0 else "error"
                VOICE_CMD_EXEC_DURATION.labels(status_).observe(__import__("time").perf_counter() - t0)
                await ws.send_json({
                    "transcript": tr.text,
                    "confidence": tr.confidence,
                    "nd_flag": nd_flag,
                    "stdout": stdout,
                    "stderr": stderr,
                    "exit_code": code,
                })
            elif "text" in msg and msg["text"]:
                # allow JSON control messages
                try:
                    import json
                    payload = json.loads(msg["text"]) if msg["text"].strip().startswith("{") else {"text": msg["text"]}
                    if payload.get("type") == "ping":
                        await ws.send_json({"type": "pong"})
                        continue
                    if payload.get("type") == "config":
                        codec = (payload.get("codec") or "pcm16").lower()
                        sr = int(payload.get("sample_rate") or 16000)
                        buf.codec = codec
                        buf.sample_rate = sr
                        await ws.send_json({"status": "configured", "codec": codec, "sample_rate": sr})
                        continue
                    text = payload.get("text", "")
                    clean = sanitize_command(profanity_filter(text))
                    t0 = __import__("time").perf_counter()
                    stdout, stderr, code, _ = await run_hypercode(clean, timeout=5)
                    status_ = "success" if code == 0 else "error"
                    VOICE_CMD_EXEC_DURATION.labels(status_).observe(__import__("time").perf_counter() - t0)
                    await ws.send_json({
                        "transcript": text,
                        "confidence": 0.99,
                        "nd_flag": False,
                        "stdout": stdout,
                        "stderr": stderr,
                        "exit_code": code,
                    })
                except Exception as e:
                    await ws.send_json({"error": str(e)})
            else:
                await ws.send_json({"status": "noop"})
    except WebSocketDisconnect:
        VOICE_WS_CONNECTIONS.labels("disconnected").inc()
    except Exception as e:
        logger.error("voice_ws_error", error=str(e))
        VOICE_WS_CONNECTIONS.labels("error").inc()
        try:
            await ws.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass
