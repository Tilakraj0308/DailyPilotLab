
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def verify():
    # 1. Create a test idea
    print("Creating test idea...")
    creation_data = {"content": "Refactor Test"}
    res = requests.post(f"{BASE_URL}/ideas", json=creation_data)
    
    time.sleep(1)
    
    # 2. Fetch to get ID
    print("Fetching to get ID...")
    res = requests.get(f"{BASE_URL}/ideas")
    try:
        all_ideas = res.json()
    except Exception as e:
        print(f"Failed to parse JSON: {res.text}")
        return

    target = next((i for i in all_ideas if i['content'] == "Refactor Test"), None)
    
    if not target:
        print("Failed to find created idea")
        return

    idea_id = target['id']
    print(f"Target Idea ID: {idea_id}")

    # 3. Test Update (Single) with ID in body
    print("Testing Single Update with ID in body...")
    update_payload = {"id": idea_id, "content": "Refactor Test Updated"}
    res = requests.post(f"{BASE_URL}/ideas/update", json=update_payload)
    print(f"Update Status: {res.status_code}")
    
    # Verify update
    res = requests.get(f"{BASE_URL}/ideas")
    updated = next((i for i in res.json() if i['id'] == idea_id), None)
    if updated['content'] != "Refactor Test Updated":
        print(f"Update failed. Content: {updated['content']}")
    else:
        print("Update Verified.")

    # 4. Test Delete (Single) with ID in body
    print("Testing Single Delete with ID in body...")
    delete_payload = {"id": idea_id}
    res = requests.post(f"{BASE_URL}/ideas/delete", json=delete_payload)
    print(f"Delete Status: {res.status_code}")

    # Verify delete
    res = requests.get(f"{BASE_URL}/ideas")
    deleted = next((i for i in res.json() if i['id'] == idea_id), None)
    if deleted:
        print("Delete failed. Idea still exists.")
    else:
        print("Delete Verified.")

if __name__ == "__main__":
    verify()
