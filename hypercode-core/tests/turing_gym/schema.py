from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from enum import Enum
import uuid
from datetime import datetime

class ValidationType(str, Enum):
    FILE_EXISTS = "file_exists"
    FILE_CONTENT_MATCH = "file_content_match"
    REGEX_MATCH = "regex_match"
    FUNCTION_CALL = "function_call"
    EXIT_CODE = "exit_code"

class ValidationRule(BaseModel):
    type: ValidationType
    target: str # File path or field name
    expected: Optional[Union[str, int, bool]] = None
    regex_pattern: Optional[str] = None
    description: Optional[str] = None

class GymTestCase(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    agent_role: str # The role of the agent to test (e.g., "coder", "writer")
    agent_config: Dict[str, Any] = {} # Overrides for the agent
    prompt: str
    validation_rules: List[ValidationRule]
    timeout_seconds: int = 60
    tags: List[str] = []

class TestStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"

class GymResult(BaseModel):
    test_case_id: str
    test_name: str
    status: TestStatus
    output: Optional[str] = None
    error_message: Optional[str] = None
    duration_seconds: float
    validation_details: List[Dict[str, Any]] = [] # Details of each rule check
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class GymReport(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    total_tests: int
    passed: int
    failed: int
    errors: int
    results: List[GymResult]
