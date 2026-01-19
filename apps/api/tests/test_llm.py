from fastapi.testclient import TestClient
from app.main import app
from app.db import init_db
import os
import pytest

client = TestClient(app)

def setup_module():
    # Use a test DB
    os.environ["GUIDELINE_DB_PATH"] = os.path.abspath("test_llm.db")
    # Enable LLM with MOCK provider
    os.environ["LLM_ENABLED"] = "1"
    os.environ["LLM_PROVIDER"] = "mock"
    
    if os.path.exists("test_llm.db"):
        os.remove("test_llm.db")
    conn = init_db()
    conn.close()
    
    # Seed data
    from app.seed import seed
    seed([])

def teardown_module():
    if os.path.exists("test_llm.db"):
        os.remove("test_llm.db")

def test_llm_mock_answer():
    # Ask a question that should trigger retrieval
    response = client.post("/chat/ask", json={
        "userId": "test",
        "role": "internal",
        "question": "What is the meals limit?"
    })
    assert response.status_code == 200
    data = response.json()
    
    # Verify Mock Answer format
    assert "Mock Answer:" in data["answer"]
    assert "Travel Policy" in data["answer"]
    
    # Verify citations are present
    assert len(data["citations"]) > 0
    assert data["confidence"] in ["High", "Medium", "Low"]

def test_llm_citation_filtering():
    # Mock provider always returns top 2 citations
    response = client.post("/chat/ask", json={
        "userId": "test",
        "role": "internal",
        "question": "What is the meals limit?"
    })
    data = response.json()
    
    # Should restrict to 2 citations as per mock logic
    assert len(data["citations"]) <= 2

def test_llm_disabled_fallback():
    # Temporarily disable LLM
    os.environ["LLM_ENABLED"] = "0"
    
    response = client.post("/chat/ask", json={
        "userId": "test",
        "role": "internal",
        "question": "What is the meals limit?"
    })
    data = response.json()
    
    # Should NOT have Mock Answer
    assert "Mock Answer:" not in data["answer"]
    # Should result in the standard template answer for meals
    assert "Meals are capped" in data["answer"]
    
    # Re-enable
    os.environ["LLM_ENABLED"] = "1"
