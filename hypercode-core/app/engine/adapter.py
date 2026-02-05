import asyncio
import time
import os
from typing import Tuple, Optional, Dict
import httpx
from contextvars import ContextVar

_INTERNAL_CALL: ContextVar[bool] = ContextVar("HC_INTERNAL_CALL", default=False)

def set_internal_call(flag: bool):
    return _INTERNAL_CALL.set(flag)

def reset_internal_call(token):
    _INTERNAL_CALL.reset(token)

async def run_hypercode(source: str, timeout: int = 30, env: Optional[Dict[str, str]] = None, target: Optional[str] = None) -> Tuple[str, str, int, float]:
    t0 = time.time()
    try:
        import sys
        mod = sys.modules.get("hypercode_engine")
        if mod and hasattr(mod, "run_code"):
            res = mod.run_code(source, target=target)
            return (
                getattr(res, "stdout", ""),
                getattr(res, "stderr", ""),
                getattr(res, "exit_code", 0),
                time.time() - t0,
            )
        api_url = os.getenv("ENGINE_API_URL", "http://localhost:8000/engine/run")
        try:
            if not _INTERNAL_CALL.get():
                async with httpx.AsyncClient(timeout=timeout) as client:
                    payload = {"source": source, "env_vars": env}
                    if target:
                        payload["target"] = target
                    resp = await client.post(api_url, json=payload)
                    data = resp.json()
                    stdout = data.get("stdout", "")
                    stderr = data.get("stderr", "")
                    code = int(data.get("exit_code", 0))
            else:
                raise RuntimeError("internal_call")
        except Exception:
                try:
                    from app.parser.hc_parser import parse
                    from app.engine.interpreter import execute_program
                    program = parse(source)
                    r = execute_program(program)
                    stdout = r.stdout
                    stderr = r.stderr
                    code = r.exit_code
                except Exception:
                    args = ["-m", "app.engine.cli", "eval", "-e", source]
                    proc = await asyncio.create_subprocess_exec(
                        "python", *args,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        env=env
                    )
                    try:
                        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
                        stdout = out.decode().strip()
                        stderr = err.decode().strip()
                        code = proc.returncode
                    except asyncio.TimeoutError:
                        proc.kill()
                        stdout = ""
                        stderr = "Execution timed out"
                        code = -1
        return stdout, stderr, code, time.time() - t0
    except Exception as e:
        return "", str(e), -1, time.time() - t0
