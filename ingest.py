"""Ingestion pipeline: load knowledge files → split → embed → persist to Chroma."""
import logging
import os
import shutil

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_aws import BedrockEmbeddings
from langchain_chroma import Chroma

from config import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    CHROMA_PERSIST_DIR,
    CHROMA_COLLECTION_NAME,
    EMBEDDING_MODEL_ID,
    MODULE_DIR,
)

logger = logging.getLogger(__name__)

# Add new knowledge sources here without touching chain logic.
# Each entry must have: path, source (short label), category.
KNOWLEDGE_SOURCES = [
    {
        "path": os.path.join(MODULE_DIR, "it_sector.txt"),
        "source": "it_sector",
        "category": "it-support",
    },
]


def _load_documents() -> list:
    docs = []
    for entry in KNOWLEDGE_SOURCES:
        path = entry["path"]
        if not os.path.exists(path):
            logger.warning("Knowledge file not found, skipping: %s", path)
            continue
        loaded = TextLoader(path, encoding="utf-8").load()
        for doc in loaded:
            doc.metadata.update({"source": entry["source"], "category": entry["category"]})
        docs.extend(loaded)
        logger.info("Loaded %d doc(s) from %s", len(loaded), path)
    if not docs:
        raise FileNotFoundError("No knowledge files could be loaded. Check KNOWLEDGE_SOURCES paths.")
    return docs


def _split_documents(docs: list) -> list:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    logger.info("Split into %d chunks (size=%d, overlap=%d)", len(chunks), CHUNK_SIZE, CHUNK_OVERLAP)
    return chunks


def _get_embeddings() -> BedrockEmbeddings:
    return BedrockEmbeddings(model_id=EMBEDDING_MODEL_ID)


def _collection_is_populated(embeddings: BedrockEmbeddings) -> bool:
    """True only when the persisted collection exists AND contains documents."""
    if not os.path.exists(CHROMA_PERSIST_DIR):
        return False
    try:
        vs = Chroma(
            collection_name=CHROMA_COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=CHROMA_PERSIST_DIR,
        )
        return len(vs.get()["ids"]) > 0
    except Exception:
        return False


def get_index_stats(vectorstore: Chroma) -> dict:
    """Return chunk count and unique source labels from the live vectorstore."""
    try:
        result = vectorstore.get(include=["metadatas"])
        sources = sorted({m.get("source", "unknown") for m in result["metadatas"]})
        return {"doc_count": len(result["ids"]), "sources": sources}
    except Exception:
        return {"doc_count": 0, "sources": []}


def build_vectorstore(force_rebuild: bool = False) -> Chroma:
    """Load the persisted Chroma index if populated; otherwise build and persist it.

    force_rebuild=True clears the existing index first, then re-embeds from all
    knowledge sources — used by the Sync button in the UI.
    """
    embeddings = _get_embeddings()

    if not force_rebuild and _collection_is_populated(embeddings):
        logger.info("Persisted index loaded from %s (embedding skipped)", CHROMA_PERSIST_DIR)
        return Chroma(
            collection_name=CHROMA_COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=CHROMA_PERSIST_DIR,
        )

    # Wipe stale data so Chroma.from_documents starts with a clean collection
    if os.path.exists(CHROMA_PERSIST_DIR):
        shutil.rmtree(CHROMA_PERSIST_DIR)
        logger.info("Cleared stale index at %s", CHROMA_PERSIST_DIR)

    logger.info("Building new vector index...")
    docs = _load_documents()
    chunks = _split_documents(docs)
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=CHROMA_COLLECTION_NAME,
        persist_directory=CHROMA_PERSIST_DIR,
    )
    logger.info("Index persisted to %s (%d chunks)", CHROMA_PERSIST_DIR, len(chunks))
    return vectorstore
