"""Session orchestration: public façade used by the Streamlit UI and tests."""
import logging
import re

from langchain_core.messages import AIMessage, ToolMessage

from chain import build_agent, get_thread_id, reset_thread
from config import validate_config
from ingest import build_vectorstore, get_index_stats

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


class ITSupportBot:
    """Public API for the IT support chatbot.

    Usage:
        bot = ITSupportBot()
        result = bot.ask("How do I set up a VPN?", session_id="user-123")
        print(result["answer"])
        print(result["sources"])
    """

    def __init__(self, force_rebuild: bool = False) -> None:
        validate_config()
        self._vectorstore = build_vectorstore(force_rebuild=force_rebuild)
        self._agent = build_agent(self._vectorstore)
        logger.info("ITSupportBot ready.")

    def ask(self, question: str, session_id: str = "default") -> dict:
        """Return {"answer": str, "sources": list[str]} for the given question."""
        if not question or not question.strip():
            return {"answer": "Please enter a valid question.", "sources": []}

        config = {"configurable": {"thread_id": get_thread_id(session_id)}}
        result = self._agent.invoke(
            {"messages": [{"role": "user", "content": question}]},
            config=config,
        )

        # Last AIMessage without pending tool_calls is the final answer
        answer = ""
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage) and not msg.tool_calls:
                answer = msg.content
                break

        # Collect deduplicated source labels embedded in tool output
        sources = sorted({
            match
            for msg in result["messages"]
            if isinstance(msg, ToolMessage)
            for match in re.findall(r"\[Source: ([^\]]+)\]", msg.content)
        })

        return {"answer": answer, "sources": sources}

    def reset_session(self, session_id: str = "default") -> None:
        """Clear conversation history by rotating to a fresh thread_id."""
        reset_thread(session_id)

    def get_index_stats(self) -> dict:
        """Return chunk count and source list from the live vectorstore."""
        return get_index_stats(self._vectorstore)

    def rebuild_index(self) -> None:
        """Force-rebuild the vector index from all knowledge sources."""
        self._vectorstore = build_vectorstore(force_rebuild=True)
        self._agent = build_agent(self._vectorstore)
        logger.info("Vector index rebuilt.")
