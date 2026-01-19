import requests
import json
import os

# Configuration matching .env
URL = "http://127.0.0.1:1234/v1/chat/completions"
MODEL = "local-model"

def test_payload():
    print(f"Testing request to {URL} with model '{MODEL}'")
    
    # 1. Simple Hello World (Verify basic chat works)
    simple_payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"}
        ],
        "temperature": 0.0
    }
    
    try:
        print("\n--- Test 1: Simple Request ---")
        resp = requests.post(URL, json=simple_payload, headers={"Content-Type": "application/json"})
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text[:500]}") # Truncate if long
        
        if resp.status_code != 200:
            return

        # 2. Complex/Large Request (Simulate actual usage with citations)
        # Verify if context length or specific payload structure is the issue
        print("\n--- Test 2: Simulated Context Request ---")
        long_context = "Word " * 1000 # ~1000 tokens
        complex_payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "You are helpful. Return JSON."},
                {"role": "user", "content": f"Context: {long_context}\n\nQuestion: Hi"}
            ],
            "temperature": 0.0
        }
        resp = requests.post(URL, json=complex_payload, headers={"Content-Type": "application/json"})
        print(f"Status: {resp.status_code}")
        if resp.status_code != 200:
             print(f"Error Response: {resp.text}")
        else:
             print("Success!")

    except Exception as e:
        print(f"Connection Exception: {e}")

if __name__ == "__main__":
    test_payload()
