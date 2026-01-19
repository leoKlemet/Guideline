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
    assert "09:00" in data["answer"]
