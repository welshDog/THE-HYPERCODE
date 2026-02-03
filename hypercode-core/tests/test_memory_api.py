import pytest
import httpx
import asyncio

# Use localhost:8000 because we run this inside the container where the app is running
BASE_URL = "http://localhost:8000/memory"

async def run_integration_test():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        print("Starting Memory API Integration Test...")
        
        # 1. Create Memory
        memory_data = {
            "content": "Test memory content",
            "type": "short-term",
            "userId": "user-integration",
            "sessionId": "session-integration",
            "keywords": ["test", "api"],
            "metadata": {"source": "integration-script"}
        }
        print(f"1. Creating memory: {memory_data}")
        response = await client.post("/", json=memory_data)
        if response.status_code != 201:
            print(f"Failed to create memory: {response.text}")
            return False
        
        created_memory = response.json()
        memory_id = created_memory["id"]
        print(f"   Created memory ID: {memory_id}")
        
        if created_memory["content"] != memory_data["content"]:
            print("Content mismatch!")
            return False

        # 2. Get Memory
        print(f"2. Retrieving memory: {memory_id}")
        response = await client.get(f"/{memory_id}")
        if response.status_code != 200:
            print(f"Failed to get memory: {response.text}")
            return False
        
        if response.json()["id"] != memory_id:
            print("ID mismatch!")
            return False

        # 3. Update Memory
        update_data = {"content": "Updated content via API"}
        print(f"3. Updating memory: {update_data}")
        response = await client.put(f"/{memory_id}", json=update_data)
        if response.status_code != 200:
            print(f"Failed to update memory: {response.text}")
            return False
        
        if response.json()["content"] != "Updated content via API":
            print("Update failed!")
            return False

        # 4. Search Memory
        print("4. Searching memory...")
        response = await client.get("/search", params={"query": "Updated", "userId": "user-integration"})
        if response.status_code != 200:
            print(f"Failed to search: {response.text}")
            return False
        
        results = response.json()
        print(f"   Found {len(results)} results")
        if len(results) == 0 or results[0]["id"] != memory_id:
            print("Search failed to find the memory")
            return False

        # 5. Delete Memory
        print(f"5. Deleting memory: {memory_id}")
        response = await client.delete(f"/{memory_id}")
        if response.status_code != 204:
            print(f"Failed to delete: {response.text}")
            return False

        # 6. Verify Deletion
        print("6. Verifying deletion...")
        response = await client.get(f"/{memory_id}")
        if response.status_code != 404:
            print("Memory still exists!")
            return False

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
