import httpx
import asyncio
import pytest

# Use localhost:8000 because we run this inside the container where the app is running
BASE_URL = "http://localhost:8000/execution"

async def run_integration_test():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=35.0) as client:
        print("Starting Execution Engine Integration Test...")
        
        # 1. Health Check
        print("1. Checking Health...")
        response = await client.get("/health")
        if response.status_code != 200:
            print(f"Health check failed: {response.text}")
            return False
        print("   Health Check Passed")

        # 2. Execute Python Code
        print("2. Executing Python Code...")
        py_req = {
            "code": "print('Hello from HyperCode')",
            "language": "python"
        }
        response = await client.post("/execute", json=py_req)
        if response.status_code != 200:
            print(f"Python execution failed: {response.text}")
            return False
        
        result = response.json()
        print(f"   Result: {result}")
        if result["stdout"] != "Hello from HyperCode" or result["status"] != "success":
            print("Python output mismatch!")
            return False

        # 3. Execute Shell Code
        print("3. Executing Shell Code...")
        sh_req = {
            "code": "echo 'Shell works too'",
            "language": "shell"
        }
        response = await client.post("/execute", json=sh_req)
        result = response.json()
        if result["stdout"] != "Shell works too":
            print("Shell output mismatch!")
            return False

        # 4. Test Error Handling (Syntax Error)
        print("4. Testing Syntax Error...")
        err_req = {
            "code": "print('Missing parenthesis",
            "language": "python"
        }
        response = await client.post("/execute", json=err_req)
        result = response.json()
        if result["status"] != "error" or "SyntaxError" not in result["stderr"]:
            print("Error handling failed!")
            return False
        print("   Syntax Error caught successfully")

        # 5. Test Timeout
        print("5. Testing Timeout (2s)...")
        timeout_req = {
            "code": "import time; time.sleep(5)",
            "language": "python",
            "timeout": 2
        }
        response = await client.post("/execute", json=timeout_req)
        result = response.json()
        if result["status"] != "timeout":
            print(f"Timeout failed! Status: {result['status']}")
            return False
        print("   Timeout caught successfully")

        print("Integration Test Passed Successfully!")
        return True

if __name__ == "__main__":
    try:
        success = asyncio.run(run_integration_test())
        if not success:
            exit(1)
    except Exception as e:
        print(f"Test failed with exception: {e}")
        exit(1)
