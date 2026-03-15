import requests
import time

BASE_URL = "http://127.0.0.1:5000/api"

def test_chaos():
    print("1. Checking Initial Queue...")
    try:
        r = requests.get(f"{BASE_URL}/queue")
        initial_len = len(r.json())
        print(f"Initial Queue Length: {initial_len}")
    except:
        initial_len = 0
        
    print("2. Triggering Chaos...")
    r = requests.post(f"{BASE_URL}/chaos")
    print(f"Status: {r.status_code}")
    print(r.text)
    
    # Wait for DB commit latency if any (though synchronous)
    time.sleep(1)
    
    print("3. Checking Final Queue...")
    r = requests.get(f"{BASE_URL}/queue")
    final_len = len(r.json())
    print(f"Final Queue Length: {final_len}")
    
    diff = final_len - initial_len
    if diff >= 15:
        print(f"[PASS] Chaos added {diff} patients successfully.")
    else:
        print(f"[FAIL] Chaos only added {diff} patients (Expected 15-20).")

if __name__ == "__main__":
    test_chaos()
