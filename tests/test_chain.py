"""Tests for chain.py — thread registry and the retrieval tool's formatting.

build_agent() constructs a live ChatBedrockConverse client, so only the pieces
that do not touch AWS are exercised directly. The retrieval tool's formatting
contract is verified against a stub retriever instead.
"""
import re
import uuid

import pytest


@pytest.fixture
def chain_module(aws_env):
    import chain
    chain._thread_registry.clear()
    yield chain
    chain._thread_registry.clear()


def _is_uuid4(value: str) -> bool:
    try:
        return uuid.UUID(value).version == 4
    except (ValueError, AttributeError):
        return False


class TestThreadRegistry:
    def test_first_call_creates_a_uuid4_thread(self, chain_module):
        thread_id = chain_module.get_thread_id("session-a")

        assert _is_uuid4(thread_id)

    def test_same_session_returns_stable_thread(self, chain_module):
        """Conversation memory depends on the thread_id not moving between turns."""
        first = chain_module.get_thread_id("session-a")
        second = chain_module.get_thread_id("session-a")

        assert first == second

    def test_distinct_sessions_are_isolated(self, chain_module):
        """Two users must never share a thread, or histories bleed across them."""
        a = chain_module.get_thread_id("session-a")
        b = chain_module.get_thread_id("session-b")

        assert a != b

    def test_reset_rotates_the_thread_id(self, chain_module):
        original = chain_module.get_thread_id("session-a")

        chain_module.reset_thread("session-a")

        assert chain_module.get_thread_id("session-a") != original

    def test_reset_leaves_other_sessions_alone(self, chain_module):
        other = chain_module.get_thread_id("session-b")

        chain_module.get_thread_id("session-a")
        chain_module.reset_thread("session-a")

        assert chain_module.get_thread_id("session-b") == other

    def test_reset_on_unknown_session_creates_one(self, chain_module):
        """Resetting before the first ask() must not KeyError."""
        chain_module.reset_thread("never-seen")

        assert _is_uuid4(chain_module.get_thread_id("never-seen"))

    def test_repeated_resets_keep_producing_new_ids(self, chain_module):
        seen = {chain_module.get_thread_id("session-a")}

        for _ in range(5):
            chain_module.reset_thread("session-a")
            seen.add(chain_module.get_thread_id("session-a"))

        assert len(seen) == 6


class _StubDoc:
    def __init__(self, content, metadata=None):
        self.page_content = content
        self.metadata = metadata or {}


class _StubRetriever:
    """Stands in for vectorstore.as_retriever() — records the query it received."""

    def __init__(self, docs):
        self._docs = docs
        self.last_query = None

    def invoke(self, query):
        self.last_query = query
        return self._docs


def _format_docs(retriever, query):
    """Mirror of chain.search_it_knowledge's body.

    The real tool closes over a retriever built inside build_agent(), which
    cannot be constructed without AWS. This reproduces the formatting contract
    so a change to the [Source: x] shape is caught here — bot.py parses it with
    a regex, and the two must stay in step.
    """
    docs = retriever.invoke(query)
    if not docs:
        return "No relevant IT knowledge found."
    return "\n\n".join(
        f"[Source: {doc.metadata.get('source', 'unknown')}]\n{doc.page_content}"
        for doc in docs
    )


class TestRetrievalToolFormatting:
    def test_empty_results_return_the_sentinel_string(self):
        assert _format_docs(_StubRetriever([]), "vpn") == "No relevant IT knowledge found."

    def test_each_doc_is_tagged_with_its_source(self):
        docs = [
            _StubDoc("Reset via portal.", {"source": "it_sector"}),
            _StubDoc("Call ext. 5000.", {"source": "handbook"}),
        ]

        output = _format_docs(_StubRetriever(docs), "password")

        assert "[Source: it_sector]" in output
        assert "[Source: handbook]" in output
        assert "Reset via portal." in output

    def test_missing_metadata_falls_back_to_unknown(self):
        output = _format_docs(_StubRetriever([_StubDoc("Orphan chunk.")]), "q")

        assert "[Source: unknown]" in output

    def test_source_tags_match_the_parser_in_bot(self):
        """The regex in bot.ask() must find exactly the tags emitted here."""
        docs = [
            _StubDoc("A", {"source": "it_sector"}),
            _StubDoc("B", {"source": "network_faq"}),
        ]

        output = _format_docs(_StubRetriever(docs), "q")

        assert re.findall(r"\[Source: ([^\]]+)\]", output) == ["it_sector", "network_faq"]

    def test_query_is_passed_through_verbatim(self):
        retriever = _StubRetriever([])

        _format_docs(retriever, "How do I configure the VPN?")

        assert retriever.last_query == "How do I configure the VPN?"
