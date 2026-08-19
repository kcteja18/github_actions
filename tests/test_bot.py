"""Tests for bot.py — the ITSupportBot façade.

__init__ calls validate_config(), build_vectorstore() (embeds via Bedrock) and
build_agent() (constructs a Bedrock client). All three are patched so the
answer-extraction and source-parsing logic can be tested without AWS.
"""
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


@pytest.fixture
def bot_factory(aws_env):
    """Build an ITSupportBot whose agent returns a scripted message list."""
    def _make(messages=None, index_stats=None):
        import bot as bot_module

        agent = MagicMock()
        agent.invoke.return_value = {"messages": messages or []}

        with patch.object(bot_module, "build_vectorstore", return_value=MagicMock()), \
             patch.object(bot_module, "build_agent", return_value=agent), \
             patch.object(bot_module, "get_index_stats", return_value=index_stats or {}):
            instance = bot_module.ITSupportBot()

        instance._agent = agent
        return instance, agent

    return _make


def _tool_msg(content):
    return ToolMessage(content=content, tool_call_id="call-1")


class TestAskValidation:
    @pytest.mark.parametrize("bad_input", ["", "   ", "\n", "\t  \n"])
    def test_blank_questions_are_rejected_without_calling_the_agent(self, bot_factory, bad_input):
        """Guards against burning a Bedrock call on whitespace."""
        instance, agent = bot_factory()

        result = instance.ask(bad_input)

        assert result == {"answer": "Please enter a valid question.", "sources": []}
        agent.invoke.assert_not_called()

    def test_valid_question_invokes_the_agent(self, bot_factory):
        instance, agent = bot_factory([AIMessage(content="Answer.")])

        instance.ask("How do I reset my password?")

        agent.invoke.assert_called_once()
        payload = agent.invoke.call_args[0][0]
        assert payload["messages"][0]["content"] == "How do I reset my password?"


class TestAnswerExtraction:
    def test_returns_the_final_ai_message(self, bot_factory):
        instance, _ = bot_factory([
            HumanMessage(content="How do I reset my password?"),
            AIMessage(content="Use the self-service portal."),
        ])

        assert instance.ask("q")["answer"] == "Use the self-service portal."

    def test_skips_the_tool_calling_ai_message(self, bot_factory):
        """The first AIMessage only requests the tool — it is not the answer."""
        tool_call_msg = AIMessage(
            content="",
            tool_calls=[{"name": "search_it_knowledge", "args": {"query": "vpn"}, "id": "call-1"}],
        )
        instance, _ = bot_factory([
            HumanMessage(content="VPN setup?"),
            tool_call_msg,
            _tool_msg("[Source: it_sector]\nInstall the client."),
            AIMessage(content="1. Install the client."),
        ])

        assert instance.ask("q")["answer"] == "1. Install the client."

    def test_returns_empty_string_when_no_ai_message_present(self, bot_factory):
        """Degenerate agent output must not raise — the UI renders the empty answer."""
        instance, _ = bot_factory([HumanMessage(content="q")])

        assert instance.ask("q")["answer"] == ""

    def test_picks_the_last_answer_across_multiple_turns(self, bot_factory):
        instance, _ = bot_factory([
            AIMessage(content="First answer."),
            HumanMessage(content="follow-up"),
            AIMessage(content="Second answer."),
        ])

        assert instance.ask("q")["answer"] == "Second answer."


class TestSourceExtraction:
    def test_parses_source_labels_from_tool_output(self, bot_factory):
        instance, _ = bot_factory([
            _tool_msg("[Source: it_sector]\nVPN steps."),
            AIMessage(content="Answer."),
        ])

        assert instance.ask("q")["sources"] == ["it_sector"]

    def test_deduplicates_and_sorts_labels(self, bot_factory):
        instance, _ = bot_factory([
            _tool_msg(
                "[Source: it_sector]\nA\n\n"
                "[Source: handbook]\nB\n\n"
                "[Source: it_sector]\nC"
            ),
            AIMessage(content="Answer."),
        ])

        assert instance.ask("q")["sources"] == ["handbook", "it_sector"]

    def test_no_tool_message_yields_no_sources(self, bot_factory):
        instance, _ = bot_factory([AIMessage(content="Answered from memory.")])

        assert instance.ask("q")["sources"] == []

    def test_sentinel_tool_output_yields_no_sources(self, bot_factory):
        """"No relevant IT knowledge found." carries no [Source: x] tags."""
        instance, _ = bot_factory([
            _tool_msg("No relevant IT knowledge found."),
            AIMessage(content="I don't have that information in my knowledge base."),
        ])

        assert instance.ask("q")["sources"] == []

    def test_collects_across_several_tool_messages(self, bot_factory):
        instance, _ = bot_factory([
            _tool_msg("[Source: it_sector]\nA"),
            _tool_msg("[Source: network_faq]\nB"),
            AIMessage(content="Answer."),
        ])

        assert instance.ask("q")["sources"] == ["it_sector", "network_faq"]


class TestSessionHandling:
    def test_thread_id_is_threaded_into_the_agent_config(self, bot_factory):
        instance, agent = bot_factory([AIMessage(content="Answer.")])

        instance.ask("q", session_id="user-123")

        thread_id = agent.invoke.call_args.kwargs["config"]["configurable"]["thread_id"]
        assert thread_id

    def test_same_session_reuses_one_thread(self, bot_factory):
        instance, agent = bot_factory([AIMessage(content="Answer.")])

        instance.ask("first", session_id="user-123")
        instance.ask("second", session_id="user-123")

        first, second = (
            c.kwargs["config"]["configurable"]["thread_id"] for c in agent.invoke.call_args_list
        )
        assert first == second

    def test_different_sessions_get_different_threads(self, bot_factory):
        instance, agent = bot_factory([AIMessage(content="Answer.")])

        instance.ask("q", session_id="user-a")
        instance.ask("q", session_id="user-b")

        first, second = (
            c.kwargs["config"]["configurable"]["thread_id"] for c in agent.invoke.call_args_list
        )
        assert first != second

    def test_reset_session_starts_a_new_thread(self, bot_factory):
        instance, agent = bot_factory([AIMessage(content="Answer.")])

        instance.ask("q", session_id="user-123")
        instance.reset_session("user-123")
        instance.ask("q", session_id="user-123")

        first, second = (
            c.kwargs["config"]["configurable"]["thread_id"] for c in agent.invoke.call_args_list
        )
        assert first != second


class TestIndexOperations:
    def test_get_index_stats_delegates_to_ingest(self, aws_env):
        import bot as bot_module

        stats = {"doc_count": 42, "sources": ["it_sector"]}
        with patch.object(bot_module, "build_vectorstore", return_value=MagicMock()), \
             patch.object(bot_module, "build_agent", return_value=MagicMock()), \
             patch.object(bot_module, "get_index_stats", return_value=stats) as mock_stats:
            instance = bot_module.ITSupportBot()

            assert instance.get_index_stats() == stats
            mock_stats.assert_called_with(instance._vectorstore)

    def test_rebuild_index_forces_rebuild_and_rewires_the_agent(self, aws_env):
        """A rebuilt store must be handed to a fresh agent, or the tool
        keeps querying the old retriever."""
        import bot as bot_module

        old_store, new_store = MagicMock(name="old"), MagicMock(name="new")
        old_agent, new_agent = MagicMock(name="old"), MagicMock(name="new")

        with patch.object(bot_module, "build_vectorstore", side_effect=[old_store, new_store]) as mock_build, \
             patch.object(bot_module, "build_agent", side_effect=[old_agent, new_agent]):
            instance = bot_module.ITSupportBot()
            instance.rebuild_index()

        assert mock_build.call_args_list[-1].kwargs == {"force_rebuild": True}
        assert instance._vectorstore is new_store
        assert instance._agent is new_agent


class TestStartupValidation:
    def test_missing_credentials_abort_construction(self, no_aws_env):
        """Fail at startup, not on the first user question."""
        import bot as bot_module

        with patch.object(bot_module, "build_vectorstore") as mock_build:
            with pytest.raises(EnvironmentError):
                bot_module.ITSupportBot()

            mock_build.assert_not_called()
