"""Smoke test: proves your Hindsight Cloud connection works. Run: python hello_memory.py"""
import os
from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()  # reads the .env file sitting next to this script

client = Hindsight(
    base_url=os.environ["HINDSIGHT_BASE_URL"],
    api_key=os.environ["HINDSIGHT_API_KEY"],
)

BANK = "smoke-test"

# --- 0. Create the memory bank (a "bank" = one product's brain) ---
try:
    client.create_bank(
        bank_id=BANK,
        name="Smoke Test",
        mission="Remember user feedback about the Finly app for testing.",
    )
    print(f"Created bank '{BANK}'")
except Exception as e:
    print(f"Bank '{BANK}' probably already exists ({type(e).__name__}) - continuing")

# --- 1. RETAIN: store a piece of feedback ---
print("\nRetaining a sample review...")
client.retain(
    bank_id=BANK,
    content=(
        "App Store review, 2 stars, March 12: 'UPI payments on Finly fail every "
        "time I'm on the metro. Started right after the v2.3 update. Fix this!'"
    ),
    metadata={"channel": "app_store", "sentiment": "negative"},
)

# --- 2. RECALL: search the memory ---
print("\nRecalling payment issues...")
results = client.recall(bank_id=BANK, query="What payment issues do users report?")
for r in results.results:
    print(f"  RECALL [{r.type}]: {r.text}")

# --- 3. REFLECT: Hindsight reasons over memories and answers ---
print("\nReflecting...")
answer = client.reflect(
    bank_id=BANK,
    query="Summarize the user complaint and when it started.",
)
print(f"  REFLECT: {answer.text}")

client.close()
print("\n✅ SUCCESS - your memory layer works! Ready for Phase 2.")