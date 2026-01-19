from fastapi.testclient import TestClient
from app.main import app
from app.db import init_db
import os

client = TestClient(app)

def setup_module():
    # Use a test DB
    os.environ["GUIDELINE_DB_PATH"] = os.path.abspath("test_guideline.db")
    if os.path.exists("test_guideline.db"):
        os.remove("test_guideline.db")
    conn = init_db()
    conn.close()
    
    # Seed data
    from app.seed import seed
    seed()

def teardown_module():
    if os.path.exists("test_guideline.db"):
        os.remove("test_guideline.db")

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}

def test_docs_seeded():
    response = client.get("/docs")
    assert response.status_code == 200
    docs = response.json()
    assert len(docs) >= 1
    assert docs[0]["title"] == "Travel Policy 2025"

def test_chat_ask_policy():
    response = client.post("/chat/ask", json={
        "userId": "test",
        "role": "internal",
        "question": "What is the meals limit?"
    })
    assert response.status_code == 200
    data = response.json()
    assert "Meals are capped at **$60/day**" in data["answer"]
    assert data["confidence"] != "Low"
    assert len(data["citations"]) > 0

def test_chat_ask_weird_question():
    response = client.post("/chat/ask", json={
        "userId": "test",
        "role": "internal",
        "question": "What is the policy on spaceships?"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["lowConfidence"] is True
    assert data["reviewId"] is not None
    
    # Verify it went to queue
    rev_response = client.get(f"/review?status=open")
    items = rev_response.json()
    assert any(i["id"] == data["reviewId"] for i in items)

def test_schedule_ask():
    response = client.post("/schedule/ask", json={"question": "schedule Monday"})
    assert response.status_code == 200
    data = response.json()
    assert "Monday" in data["answer"]
    assert "08:00" in data["answer"]

def test_schedule_ask_holiday_january():
    # As per seed data, 2026-01-01 is New Year's Day
    response = client.post("/schedule/ask", json={"question": "Any holidays in January?"})
    assert response.status_code == 200
    data = response.json()
    assert "New Year's Day" in data["answer"]
    assert "2026-01-01" in data["answer"]

def test_schedule_ask_holiday_december():
    # As per seed data, 2026-12-25 is Christmas Day
    response = client.post("/schedule/ask", json={"question": "Any holidays in December?"})
    assert response.status_code == 200
    data = response.json()
    assert "Christmas Day" in data["answer"]
    assert "2026-12-25" in data["answer"]

def test_schedule_ask_next_holiday_logic():
    # This test assumes the implementation will use the current time. 
    # Since we can't easily mock time inside the seeded app without more work, 
    # we rely on the fact that the seed data is in 2026.
    # Current "real" time in context is 2026-01-19.
    # So "next holiday" should NOT be New Year's Day (2026-01-01), but Personal Day (2026-04-03) or similar.
    
    response = client.post("/schedule/ask", json={"question": "When is the next holiday?"})
    assert response.status_code == 200
    data = response.json()
    # Should NOT satisfy New Year's Day as it is passed
    assert "New Year's Day" not in data["answer"] 
    # Should satisfy Personal Day (2026-04-03)
    assert "Personal Day" in data["answer"]

