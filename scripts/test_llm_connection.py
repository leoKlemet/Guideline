import requests
import sys

URL = "http://127.0.0.1:1234/v1/models"

def test_connection():
    print(f"Testing connection to LM Studio at {URL}...")
    try:
        response = requests.get(URL, timeout=2)
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS: Connected to LM Studio!")
            print(f"Available Models: {[m['id'] for m in data.get('data', [])]}")
            return True
        else:
            print(f"❌ ERROR: Server reachable but returned {response.status_code}")
            print(response.text)
            return False
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Could not connect to localhost:1234.")
        print("   -> Is LM Studio running?")
        print("   -> Did you click 'Start Server' in the Local Server tab?")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
