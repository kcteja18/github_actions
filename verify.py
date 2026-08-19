"""Verification script — run once to confirm all flows work end-to-end."""
from langchain_core.messages import AIMessage, ToolMessage
from bot import ITSupportBot

bot = ITSupportBot()

print("=== Test 1: Known answer ===")
r = bot.ask("How do I troubleshoot network connectivity issues?", session_id="test")
print("Answer:", r["answer"][:300])
print("Sources:", r["sources"])
assert r["answer"], "answer must not be empty"

print()
print("=== Test 2: Multi-turn follow-up ===")
r2 = bot.ask("What should I check first?", session_id="test")
print("Answer:", r2["answer"][:300])
print("Sources:", r2["sources"])
assert r2["answer"], "answer must not be empty"

print()
print("=== Test 3: Out-of-scope question ===")
r3 = bot.ask("What is the capital of France?", session_id="test")
print("Answer:", r3["answer"][:300])
assert (
    "helpdesk" in r3["answer"].lower() or "knowledge base" in r3["answer"].lower()
), "out-of-scope must trigger fallback message"
print("Fallback message: OK")

print()
print("=== Test 4: Empty input guard ===")
r4 = bot.ask("   ", session_id="test")
assert r4["answer"] == "Please enter a valid question."
print("Empty input guard: OK")

print()
print("=== Test 5: Session reset ===")
bot.reset_session("test")
print("reset_session: OK")

print()
print("All 5 tests PASSED.")
