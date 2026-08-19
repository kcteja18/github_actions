## Plan: Modern LangChain IT Bot

Build the IT support chatbot as a reusable backend module plus a Streamlit UI, keeping AWS Bedrock as the provider and removing all dependence on the legacy patterns currently used in [12_ChatWithPDF/langchain_app.py](12_ChatWithPDF/langchain_app.py#L1) and [12_ChatWithPDF/streamlit_app.py](12_ChatWithPDF/streamlit_app.py#L1). The recommended approach uses the current LangChain package split and Runnable-based retrieval flow so the bot is production-oriented, extensible beyond [13_ITSupportChatbot/it_sector.txt](13_ITSupportChatbot/it_sector.txt#L1), and avoids `langchain_classic` entirely.

**Steps**
1. Phase 1: Replace the current dependency model in [12_ChatWithPDF/requirements.txt](12_ChatWithPDF/requirements.txt#L1) with latest-package equivalents: `langchain`, `langchain-community`, `langchain-text-splitters`, `langchain-aws`, and a persisted vector-store dependency, with config validated from environment variables at startup.
2. Phase 2: Turn [13_ITSupportChatbot/it_sector.txt](13_ITSupportChatbot/it_sector.txt#L1) into the first source in an extensible ingestion pipeline, attaching metadata so future knowledge files can be added without changing the chain logic.
3. Phase 3: Author a dedicated IT-support system prompt and prompt composition layer using `ChatPromptTemplate` and `MessagesPlaceholder`, use `Middlewares`, `Agents`, `Tools` and `Runnables` with clear rules for grounded answers, escalation guidance, and safe fallback when the answer is absent.
4. Phase 4: Migrate the chatbot architecture off `ConversationalRetrievalChain` into the modern composition path: embeddings, retriever, history-aware retriever, answer chain, retrieval chain, and `RunnableWithMessageHistory`. This is the core replacement for the legacy flow in [12_ChatWithPDF/langchain_app.py](12_ChatWithPDF/langchain_app.py#L1).
5. Phase 5: Split the implementation under the IT chatbot folder into small backend modules for config, ingestion, prompt assembly, retriever/chain wiring, and session orchestration, then keep Streamlit as a thin UI wrapper.
6. Phase 6: Harden for production-style behavior with persisted indexing, source attribution, structured logging, optional LangSmith tracing, config knobs for chunking/retrieval/model IDs, and explicit handling for empty retrievals and document-side prompt injection attempts.
7. Phase 7: Verify with a narrow app check that indexes the IT content, answers representative support questions, preserves/reset chat history correctly, and contains no `langchain_classic` imports in the new implementation slice.

**Relevant files**
- [12_ChatWithPDF/langchain_app.py](12_ChatWithPDF/langchain_app.py#L1) is the migration reference because it shows the exact legacy LangChain constructs that need to be removed.
- [12_ChatWithPDF/streamlit_app.py](12_ChatWithPDF/streamlit_app.py#L1) is the UI reference to preserve the repo’s current app shape while moving business logic out of the UI layer.
- [12_ChatWithPDF/requirements.txt](12_ChatWithPDF/requirements.txt#L1) is the current dependency baseline.
- [13_ITSupportChatbot/it_sector.txt](13_ITSupportChatbot/it_sector.txt#L1) is the initial knowledge source.
- [docs/chroma](docs/chroma) is a useful hint that persisted local Chroma is already consistent with this workspace, and is the better default than FAISS if the goal is a more production-oriented local setup.

**Verification**
1. Confirm the new IT chatbot code imports only modern LangChain packages and does not reference `langchain_classic`.
2. Rebuild the local vector index from the IT support content and test at least three flows: a known answer, a multi-turn follow-up, and an out-of-scope question.
3. Start the Streamlit app and verify initialization, chat continuity, reset behavior, and safe no-answer handling.
4. If tracing is enabled, verify that retrieval inputs, retrieved context, and response timing are visible without leaking secrets.

**Decisions**
- Runtime: reusable backend module plus Streamlit UI.
- Provider: AWS Bedrock.
- Knowledge scope: start with the IT text file, but structure the bot for future document expansion.
- Included: prompt design, modern LangChain chain composition, retrieval/indexing design, app structure, and verification.
- Excluded unless requested later: deployment, auth, ticketing integrations, and multi-user persistence.

The plan is saved in session memory and ready for handoff. If you want, I can now refine one of these before implementation starts:
1. Specify the exact production file structure under the IT chatbot folder.
2. Draft the final system prompt requirements in more detail.
3. Adjust the plan toward a more API-first architecture instead of Streamlit-first.
