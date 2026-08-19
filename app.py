"""Thin Streamlit UI — all business logic lives in bot.py."""
import streamlit as st

from bot import ITSupportBot

_SESSION_ID = "streamlit_default"

st.set_page_config(
    page_title="IT Support Chatbot",
    page_icon="🖥️",
    layout="centered",
)

st.title("IT Support Chatbot")
st.caption("Powered by AWS Bedrock · LangChain · Chroma")


@st.cache_resource(show_spinner="Initializing knowledge base…")
def _get_bot() -> ITSupportBot:
    return ITSupportBot()


bot = _get_bot()

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Controls")

    if st.button("🔄 Reset Chat"):
        st.session_state.messages = []
        bot.reset_session(_SESSION_ID)
        st.success("Chat history cleared.")

    st.markdown("---")
    st.subheader("Knowledge Base")

    stats = bot.get_index_stats()
    st.metric("Indexed chunks", stats["doc_count"])
    if stats["sources"]:
        st.caption("Sources: " + ", ".join(stats["sources"]))

    if st.button("🔄 Sync Knowledge Base", help="Re-embed all knowledge sources and update the index"):
        with st.spinner("Syncing knowledge base…"):
            bot.rebuild_index()
        st.success(f"Sync complete — {bot.get_index_stats()['doc_count']} chunks indexed.")
        st.rerun()

    st.markdown("---")
    st.markdown("**Topics I can help with:**")
    st.markdown(
        "- Network connectivity\n"
        "- Software installation & configuration\n"
        "- System performance\n"
        "- Data backup & recovery\n"
        "- Email setup & troubleshooting\n"
        "- Security & antivirus\n"
        "- Hardware diagnostics\n"
        "- VPN setup\n"
        "- Mobile device support"
    )

# ── Chat history init ─────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Render existing messages ──────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("sources"):
            st.caption(f"Sources: {', '.join(msg['sources'])}")

# ── Chat input ────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Describe your IT issue…"):
    # Render and store user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Get and render assistant response
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            result = bot.ask(prompt, session_id=_SESSION_ID)
        print(result)
        
        # Extract text from answer if it's a list of content blocks
        answer_text = result["answer"]
        if isinstance(answer_text, list):
            answer_text = "".join(
                block["text"] for block in answer_text if block.get("type") == "text"
            )
        
        st.write(answer_text)
        if result["sources"]:
            st.caption(f"Sources: {', '.join(result['sources'])}")

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer_text,
            "sources": result["sources"],
        }
    )
