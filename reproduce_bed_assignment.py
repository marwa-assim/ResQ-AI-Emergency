import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000/api"

def test_bed_flow():
    # 1. Triage a patient to get them in the system
    pid = f"TEST-BED-{int(time.time())}"
    print(f"1. Creating Patient {pid}...")
    requests.post(f"{BASE_URL}/triage", json={
        "patient_id": pid, "name": "Bed Tester", "age": 50,
        "hr": 80, "spo2": 98, "sys_bp": 120, "dia_bp": 80
    })
    
    print("2. Assigning to Bed 1...")
    r = requests.post(f"{BASE_URL}/assign", json={
        "patient_id": pid,
        "bed_id": 1
    })
    print(f"Assignment Status: {r.status_code}")
    print(r.text)
    
    # 3. Check Beds API (This is what the Dashboard sees)
    print("3. Fetching /api/beds...")
    r = requests.get(f"{BASE_URL}/beds")
    beds = r.json()
    
    # Find Bed 1
    target_bed = next((b for b in beds if b['id'] == 1), None)
    print("\n--- BED 1 DATA ---")
    print(json.dumps(target_bed, indent=2))
    
    if target_bed and target_bed.get('patient_id') == pid:
        print("\n[INFO] Backend has correct assignment.")
        if not target_bed.get('name'):
            print("[ERROR] Patient Name is MISSING in bed data!")
        else:
            print(f"[INFO] Patient Name is present: {target_bed['name']}")
    else:
        print("\n[FAIL] Bed 1 is not assigned to our patient.")

if __name__ == "__main__":
    test_bed_flow()
