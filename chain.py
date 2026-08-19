"""Agent wiring: IT retrieval tool + create_agent harness with InMemorySaver checkpointer."""
import logging
import uuid

from langchain.agents import create_agent
from langchain.agents.middleware import ModelRetryMiddleware
from langchain.tools import tool
from langchain_aws import ChatBedrockConverse  # Converse API required for tool calling
from langchain_chroma import Chroma
from langgraph.checkpoint.memory import InMemorySaver

from config import CHAT_MODEL_ID, RETRIEVAL_K
from prompts import IT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

_checkpointer = InMemorySaver()

# Maps logical session_id → active LangGraph thread_id; rotate on reset
_thread_registry: dict[str, str] = {}


def get_thread_id(session_id: str) -> str:
    if session_id not in _thread_registry:
        _thread_registry[session_id] = str(uuid.uuid4())
    return _thread_registry[session_id]


def reset_thread(session_id: str) -> None:
    """Assign a fresh thread_id so the agent starts a new conversation for this session."""
    _thread_registry[session_id] = str(uuid.uuid4())
    logger.info("Thread reset for session '%s'", session_id)


def build_agent(vectorstore: Chroma):
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": RETRIEVAL_K},
    )

    @tool
    def search_it_knowledge(query: str) -> str:
        """Search the IT support knowledge base for answers to technical questions."""
        docs = retriever.invoke(query)
        if not docs:
            return "No relevant IT knowledge found."
        return "\n\n".join(
            f"[Source: {doc.metadata.get('source', 'unknown')}]\n{doc.page_content}"
            for doc in docs
        )

    return create_agent(
        model=ChatBedrockConverse(model_id=CHAT_MODEL_ID, temperature=0),
        tools=[search_it_knowledge],
        system_prompt=IT_SYSTEM_PROMPT,
        checkpointer=_checkpointer,
        middleware=[ModelRetryMiddleware(max_retries=3)],
        name="it_support_agent",
    )
