from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class Language(str, Enum):
    PYTHON = "python"
    SHELL = "shell"
    BASH = "bash"
    HYPERCODE = "hypercode"

class ExecutionRequest(BaseModel):
    code: str = Field(..., description="The code snippet to execute")
    language: Language = Field(default=Language.PYTHON, description="Programming language or shell")
    env_vars: Optional[Dict[str, str]] = Field(default=None, description="Environment variables for the execution")
    timeout: int = Field(default=30, ge=1, le=300, description="Execution timeout in seconds")
    target: Optional[str] = Field(default=None, description="HyperCode backend target: python|rust|mojo")

class ExecutionResult(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    status: str = Field(..., description="success, error, timeout")
    duration: float = Field(..., description="Execution duration in seconds")
    language: Language
