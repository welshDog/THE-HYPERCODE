import asyncio
import logging
import time
import re
import docker
from typing import List
from tests.turing_gym.schema import GymTestCase, GymResult, TestStatus, ValidationType, GymReport
from tests.turing_gym.pool_manager import WarmPoolManager
from app.core.security import create_access_token # Import auth util

logger = logging.getLogger(__name__)

class GymRunner:
    def __init__(self, docker_client=None, use_pool=True):
        self.docker = docker_client or docker.from_env()
        self.pool_manager = WarmPoolManager(self.docker) if use_pool else None
        
        if self.pool_manager:
            self.pool_manager.start()
            
    def shutdown(self):
        if self.pool_manager:
            self.pool_manager.stop()
        
    async def run_suite(self, test_cases: List[GymTestCase]) -> GymReport:
        results = []
        try:
            for test in test_cases:
                result = await self.run_test(test)
                results.append(result)
        finally:
            self.shutdown()
            
        return GymReport(
            total_tests=len(results),
            passed=len([r for r in results if r.status == TestStatus.PASSED]),
            failed=len([r for r in results if r.status == TestStatus.FAILED]),
            errors=len([r for r in results if r.status == TestStatus.ERROR]),
            results=results
        )
    
    async def run_test(self, test: GymTestCase) -> GymResult:
        logger.info(f"Running Turing Gym Test: {test.name}")
        start_time = time.time()
        container = None
        pooled_obj = None
        
        try:
            # 0. Generate Identity Token
            # Create a token for this test execution so the agent can talk back to Core
            agent_token = create_access_token(
                subject=f"gym-test-{test.id}",
                scopes=["agent", test.agent_role]
            )
            
            # Prepare Environment
            env_vars = test.agent_config.copy()
            env_vars["HYPERCODE_API_TOKEN"] = agent_token
            
            # 1. Spin up agent container (Mock or Real)
            image_name = f"hypercode-v20-{test.agent_role}-agent" 
            
            # Use Pool if available
            if self.pool_manager:
                pooled_obj = self.pool_manager.get_container(image_name)
                container = pooled_obj.container
                # Note: Ideally we'd inject token here. 
                # Since container is already running, we might need to exec a command 
                # or rely on the agent fetching config from an endpoint.
                # For MVP, we'll assume we can't easily inject ENV into running container without restart.
                # Real fix: Agent checks a mounted volume or endpoint for token.
            else:
                # Fallback for dev
                try:
                    self.docker.images.get(image_name)
                except docker.errors.ImageNotFound:
                    logger.warning(f"Image {image_name} not found. Using python:3.11-slim for simulation.")
                    image_name = "python:3.11-slim"

                container = self.docker.containers.run(
                    image_name,
                    command="tail -f /dev/null", 
                    detach=True,
                    environment=env_vars # Inject Token Here
                )
            
            # 2. Execute Prompt/Task
            # Since we don't have a real Agent API in the python-slim fallback,
            # we will simulate the "Agent's Work" by running a command directly if it's a simple script test.
            # If it were a real agent, we'd POST to http://container_ip:8000/chat
            
            # SIMULATION LOGIC FOR MVP:
            # If the prompt says "Write a Python script...", we manually write it to simulate the agent working.
            # This allows us to test the *Validation Framework* even without the full Agent connected yet.
            if "Write a Python script" in test.prompt:
                # Simulate agent success
                filename = "hello.py" # Hardcoded for the Hello World scenario
                content = "print('Hello HyperCode')"
                container.exec_run(f"sh -c 'echo \"{content}\" > {filename}'")
            
            # 3. Validate Results
            validation_details = []
            overall_status = TestStatus.PASSED
            
            for rule in test.validation_rules:
                rule_result = self._validate_rule(container, rule)
                validation_details.append(rule_result)
                if not rule_result["passed"]:
                    overall_status = TestStatus.FAILED
            
            duration = time.time() - start_time
            return GymResult(
                test_case_id=test.id,
                test_name=test.name,
                status=overall_status,
                duration_seconds=duration,
                validation_details=validation_details
            )
            
        except Exception as e:
            logger.error(f"Test error: {e}")
            return GymResult(
                test_case_id=test.id,
                test_name=test.name,
                status=TestStatus.ERROR,
                error_message=str(e),
                duration_seconds=time.time() - start_time
            )
        finally:
            if self.pool_manager and pooled_obj:
                self.pool_manager.release_container(pooled_obj)
            elif container:
                try:
                    container.kill()
                    container.remove()
                except:
                    pass

    def _validate_rule(self, container, rule) -> dict:
        result = {"type": rule.type, "passed": False, "details": ""}
        
        try:
            if rule.type == ValidationType.FILE_EXISTS:
                exit_code, _ = container.exec_run(f"test -f {rule.target}")
                result["passed"] = (exit_code == 0)
                result["details"] = f"File {rule.target} exists check: {'Yes' if exit_code==0 else 'No'}"
                
            elif rule.type == ValidationType.FILE_CONTENT_MATCH:
                exit_code, output = container.exec_run(f"cat {rule.target}")
                if exit_code != 0:
                    result["passed"] = False
                    result["details"] = "File not found"
                else:
                    content = output.decode().strip()
                    if rule.expected:
                        result["passed"] = (content == rule.expected)
                    elif rule.regex_pattern:
                        result["passed"] = bool(re.search(rule.regex_pattern, content))
                    result["details"] = f"Content: {content}"
                    
        except Exception as e:
            result["details"] = str(e)
            
        return result
