import httpx
import sys

def verify_schedule():
    try:
        response = httpx.get("http://localhost:8000/schedule")
        if response.status_code != 200:
            print(f"Error: Status code {response.status_code}")
            sys.exit(1)
        
        data = response.json()
        print("Schedule Config:")
        print(f"Timezone: {data.get('timezone')}")
        
        week = data.get('week', [])
        print(f"Week Days: {len(week)}")
        
        holidays = data.get('holidays', [])
        print(f"Holidays: {len(holidays)}")
        for h in holidays:
            print(f"  - {h['date']}: {h['name']}")
            
        # Assertions
        assert data.get('timezone'), "Timezone missing"
        assert len(week) > 0, "Week config missing"
        assert len(holidays) > 0, "Holidays missing"
        
        print("\nVerification Passed!")
    except Exception as e:
        print(f"Verification Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_schedule()
