from app.retrieval import build_answer
from app.schema import AccessLevel
import os
from dotenv import load_dotenv

# Load env vars (simulating main.py)
load_dotenv()

# Mock citations mimicking what the vector search would return
citations = [
    {
        "docTitle": "Expense Policy 2024",
        "pageStart": 5,
        "content": "Employees are granted a daily meal allowance of $75 while traveling. Receipts must be uploaded for any meal over $25."
    }
]

question = "What is the meal allowance?"
print(f"Question: {question}")
print("-" * 20)

try:
    print("Generating...")
    answer = build_answer(question, citations, "internal")
    print("Answer from LM Studio:")
    print(answer)
except Exception as e:
    print(f"Error calling build_answer: {e}")

print("\nDebug: Testing LM Studio connection...")

