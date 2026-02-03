import asyncio
import time
import structlog
from typing import Tuple
from app.schemas.execution import ExecutionRequest, ExecutionResult, Language

logger = structlog.get_logger()

class ExecutionService:
    @staticmethod
    async def execute_code(request: ExecutionRequest) -> ExecutionResult:
        logger.info("executing_code", language=request.language)
        start_time = time.time()
        
        try:
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
        
        return ExecutionResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            status=status,
            duration=duration,
            language=request.language
        )

    @staticmethod
    def _build_command(request: ExecutionRequest) -> Tuple[str, list]:
        if request.language == Language.PYTHON:
            return "python", ["-c", request.code]
        elif request.language in [Language.SHELL, Language.BASH]:
            return "bash", ["-c", request.code]
        else:
            raise ValueError(f"Unsupported language: {request.language}")
