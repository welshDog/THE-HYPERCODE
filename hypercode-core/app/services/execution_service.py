import asyncio
import time
import structlog
from typing import Tuple
from app.schemas.execution import ExecutionRequest, ExecutionResult, Language
from app.engine.adapter import run_hypercode

logger = structlog.get_logger()

LAST_RESULT: ExecutionResult | None = None

class ExecutionService:
    @staticmethod
    async def execute_code(request: ExecutionRequest) -> ExecutionResult:
        logger.info("executing_code", language=request.language)
        start_time = time.time()
        
        try:
            if request.language == Language.HYPERCODE:
                if request.target:
                    cmd, args = ExecutionService._build_command(request)
                    process = await asyncio.create_subprocess_exec(
                        cmd, *args,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        env=request.env_vars
                    )
                    try:
                        stdout_data, stderr_data = await asyncio.wait_for(
                            process.communicate(), 
                            timeout=request.timeout
                        )
                        stdout = stdout_data.decode().strip()
                        stderr = stderr_data.decode().strip()
                        exit_code = process.returncode
                        status = "success" if exit_code == 0 else "error"
                    except asyncio.TimeoutError:
                        process.kill()
                        stdout = ""
                        stderr = "Execution timed out"
                        exit_code = -1
                        status = "timeout"
                        logger.warning("execution_timeout", timeout=request.timeout)
                else:
                    stdout, stderr, exit_code, _ = await run_hypercode(
                        request.code, timeout=request.timeout, env=request.env_vars, target=request.target
                    )
                    status = "success" if exit_code == 0 else ("timeout" if exit_code == -1 and "timed out" in stderr.lower() else "error")
            else:
                cmd, args = ExecutionService._build_command(request)
                process = await asyncio.create_subprocess_exec(
                    cmd, *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=request.env_vars
                )
                try:
                    stdout_data, stderr_data = await asyncio.wait_for(
                        process.communicate(), 
                        timeout=request.timeout
                    )
                    stdout = stdout_data.decode().strip()
                    stderr = stderr_data.decode().strip()
                    exit_code = process.returncode
                    status = "success" if exit_code == 0 else "error"
                except asyncio.TimeoutError:
                    process.kill()
                    stdout = ""
                    stderr = "Execution timed out"
                    exit_code = -1
                    status = "timeout"
                    logger.warning("execution_timeout", timeout=request.timeout)

        except Exception as e:
            logger.error("execution_failed", error=str(e))
            stdout = ""
            stderr = str(e)
            exit_code = -1
            status = "error"

        duration = time.time() - start_time
        
        result = ExecutionResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            status=status,
            duration=duration,
            language=request.language
        )
        global LAST_RESULT
        LAST_RESULT = result
        return result

    @staticmethod
    def _build_command(request: ExecutionRequest) -> Tuple[str, list]:
        if request.language == Language.PYTHON:
            return "python", ["-c", request.code]
        elif request.language in [Language.SHELL, Language.BASH]:
            code = request.code.strip()
            if code.startswith("python -c"):
                rest = code[len("python -c"):].strip()
                if rest.startswith("\"") and rest.endswith("\""):
                    rest = rest[1:-1]
                if rest.startswith("'") and rest.endswith("'"):
                    rest = rest[1:-1]
                return "python", ["-c", rest]
            return "bash", ["-c", code]
        elif request.language == Language.HYPERCODE:
            args = ["-m", "app.engine.cli", "eval", "-e", request.code]
            if request.target:
                args.extend(["-t", request.target])
            return "python", args
        else:
            raise ValueError(f"Unsupported language: {request.language}")
