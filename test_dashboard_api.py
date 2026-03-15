import requests
import time
import sys

BASE_URL = "http://127.0.0.1:5000"

def test_flow():
    # 1. Submit Patient
    print("Submitting patient...")
    payload = {
        "name": "Test Patient",
        "age": 30,
        "hr": 80, "spo2": 98, "sys_bp": 120, "dia_bp": 80,
        "chronic": False, "allergy": False
    }
    try:
        r = requests.post(f"{BASE_URL}/api/triage", json=payload)
        r.raise_for_status()
        print("Submission OK")
    except Exception as e:
        print(f"Submission Failed: {e}")
        return

    # 2. Check Queue
    time.sleep(1)
    print("Fetching queue...")
    try:
        r = requests.get(f"{BASE_URL}/api/queue")
        data = r.json()
        
        if not data:
            print("Queue is empty!")
            return

        patient = data[0]
        print("Queue Data:", patient)
        
        if "vitals" in patient and "hr" in patient["vitals"]:
            print("SUCCESS: Vitals found in logic.")
        else:
            print("FAILURE: Vitals missing from response.")
            
    except Exception as e:
        print(f"Queue Check Failed: {e}")

if __name__ == "__main__":
    test_flow()
