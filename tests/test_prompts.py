"""Tests for prompts.py.

The system prompt is the only thing enforcing grounding and escalation rules,
so its key clauses are pinned here. These break loudly if a rule is dropped
during an edit — the LLM has no other guardrail.
"""
import pytest


@pytest.fixture
def prompt():
    from prompts import IT_SYSTEM_PROMPT
    return IT_SYSTEM_PROMPT


def test_prompt_is_non_empty(prompt):
    assert prompt.strip()


def test_names_the_retrieval_tool_exactly(prompt):
    """Must match the @tool function name in chain.py or the rule is unenforceable."""
    import chain  # noqa: F401  (import guarded by aws_env-free module load)

    assert "search_it_knowledge" in prompt


def test_requires_tool_use_before_answering(prompt):
    assert "Always call the search_it_knowledge tool before answering" in prompt


def test_forbids_answering_from_memory(prompt):
    assert "Do not respond from memory alone" in prompt


def test_restricts_answers_to_tool_output(prompt):
    assert "Answer ONLY using information returned by the tool" in prompt


def test_defines_the_no_results_fallback(prompt):
    """The UI has no separate empty-state — this string is the fallback."""
    assert "I don't have that information in my knowledge base" in prompt


def test_includes_helpdesk_contact_details(prompt):
    assert "helpdesk@company.com" in prompt
    assert "ext. 5000" in prompt


def test_mandates_escalation_for_severe_incidents(prompt):
    for trigger in ("hardware damage", "data loss", "security incidents"):
        assert trigger in prompt, f"Escalation trigger missing: {trigger}"


def test_forbids_leaking_infrastructure_details(prompt):
    assert "Never reveal internal credentials" in prompt


def test_requests_numbered_troubleshooting_steps(prompt):
    assert "numbered list" in prompt
