"""Tests for ingest.py — loading, splitting, and index lifecycle.

_get_embeddings() builds a live BedrockEmbeddings client, so it is patched
everywhere. Splitting is exercised for real: RecursiveCharacterTextSplitter is
pure text processing and needs no credentials.
"""
import os
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def ingest_module(aws_env):
    import ingest
    return ingest


@pytest.fixture
def knowledge_file(tmp_path):
    path = tmp_path / "kb.txt"
    path.write_text(
        "VPN Setup\n\nInstall the corporate VPN client from the software portal.\n\n"
        "Password Reset\n\nUse the self-service portal at reset.company.com.\n",
        encoding="utf-8",
    )
    return path


class TestLoadDocuments:
    def test_loads_and_stamps_metadata(self, ingest_module, knowledge_file):
        sources = [{"path": str(knowledge_file), "source": "kb", "category": "it-support"}]

        with patch.object(ingest_module, "KNOWLEDGE_SOURCES", sources):
            docs = ingest_module._load_documents()

        assert len(docs) == 1
        assert docs[0].metadata["source"] == "kb"
        assert docs[0].metadata["category"] == "it-support"
        assert "VPN Setup" in docs[0].page_content

    def test_missing_file_is_skipped_not_fatal(self, ingest_module, knowledge_file, tmp_path):
        """One broken entry must not sink an otherwise valid source list."""
        sources = [
            {"path": str(tmp_path / "gone.txt"), "source": "gone", "category": "it"},
            {"path": str(knowledge_file), "source": "kb", "category": "it-support"},
        ]

        with patch.object(ingest_module, "KNOWLEDGE_SOURCES", sources):
            docs = ingest_module._load_documents()

        assert [d.metadata["source"] for d in docs] == ["kb"]

    def test_raises_when_nothing_could_be_loaded(self, ingest_module, tmp_path):
        """Silently embedding zero documents would yield an index that answers nothing."""
        sources = [{"path": str(tmp_path / "gone.txt"), "source": "gone", "category": "it"}]

        with patch.object(ingest_module, "KNOWLEDGE_SOURCES", sources):
            with pytest.raises(FileNotFoundError, match="No knowledge files"):
                ingest_module._load_documents()

    def test_multiple_sources_are_all_loaded(self, ingest_module, tmp_path):
        first, second = tmp_path / "a.txt", tmp_path / "b.txt"
        first.write_text("Alpha content.", encoding="utf-8")
        second.write_text("Beta content.", encoding="utf-8")
        sources = [
            {"path": str(first), "source": "alpha", "category": "it"},
            {"path": str(second), "source": "beta", "category": "hr"},
        ]

        with patch.object(ingest_module, "KNOWLEDGE_SOURCES", sources):
            docs = ingest_module._load_documents()

        assert sorted(d.metadata["source"] for d in docs) == ["alpha", "beta"]

    def test_shipped_knowledge_file_exists_and_loads(self, ingest_module):
        """Guards the real it_sector.txt entry — a rename would break ingestion."""
        entry = ingest_module.KNOWLEDGE_SOURCES[0]

        assert os.path.exists(entry["path"]), f"Missing knowledge file: {entry['path']}"

        docs = ingest_module._load_documents()
        assert docs and docs[0].page_content.strip()


class TestSplitDocuments:
    def test_long_document_is_chunked(self, ingest_module, knowledge_file):
        sources = [{"path": str(knowledge_file), "source": "kb", "category": "it"}]
        with patch.object(ingest_module, "KNOWLEDGE_SOURCES", sources):
            docs = ingest_module._load_documents()

        with patch.object(ingest_module, "CHUNK_SIZE", 50), \
             patch.object(ingest_module, "CHUNK_OVERLAP", 10):
            chunks = ingest_module._split_documents(docs)

        assert len(chunks) > 1

    def test_chunks_respect_the_configured_size(self, ingest_module, knowledge_file):
        sources = [{"path": str(knowledge_file), "source": "kb", "category": "it"}]
        with patch.object(ingest_module, "KNOWLEDGE_SOURCES", sources):
            docs = ingest_module._load_documents()

        with patch.object(ingest_module, "CHUNK_SIZE", 60), \
             patch.object(ingest_module, "CHUNK_OVERLAP", 10):
            chunks = ingest_module._split_documents(docs)

        # The splitter may exceed the target when no separator exists in range;
        # a generous ceiling still catches a mis-wired size knob.
        assert all(len(c.page_content) <= 120 for c in chunks)

    def test_metadata_survives_splitting(self, ingest_module, knowledge_file):
        """Source labels must reach the vectorstore — bot.py cites them."""
        sources = [{"path": str(knowledge_file), "source": "kb", "category": "it-support"}]
        with patch.object(ingest_module, "KNOWLEDGE_SOURCES", sources):
            docs = ingest_module._load_documents()

        with patch.object(ingest_module, "CHUNK_SIZE", 50), \
             patch.object(ingest_module, "CHUNK_OVERLAP", 10):
            chunks = ingest_module._split_documents(docs)

        assert all(c.metadata["source"] == "kb" for c in chunks)

    def test_short_document_stays_a_single_chunk(self, ingest_module, tmp_path):
        path = tmp_path / "tiny.txt"
        path.write_text("Short.", encoding="utf-8")
        sources = [{"path": str(path), "source": "tiny", "category": "it"}]

        with patch.object(ingest_module, "KNOWLEDGE_SOURCES", sources):
            docs = ingest_module._load_documents()
        chunks = ingest_module._split_documents(docs)

        assert len(chunks) == 1


class TestCollectionIsPopulated:
    def test_false_when_persist_dir_absent(self, ingest_module, tmp_path):
        with patch.object(ingest_module, "CHROMA_PERSIST_DIR", str(tmp_path / "nope")):
            assert ingest_module._collection_is_populated(MagicMock()) is False

    def test_false_when_collection_is_empty(self, ingest_module, tmp_path):
        """An empty dir must trigger a rebuild, not load a store with no vectors."""
        store = MagicMock()
        store.get.return_value = {"ids": []}

        with patch.object(ingest_module, "CHROMA_PERSIST_DIR", str(tmp_path)), \
             patch.object(ingest_module, "Chroma", return_value=store):
            assert ingest_module._collection_is_populated(MagicMock()) is False

    def test_true_when_collection_has_documents(self, ingest_module, tmp_path):
        store = MagicMock()
        store.get.return_value = {"ids": ["a", "b"]}

        with patch.object(ingest_module, "CHROMA_PERSIST_DIR", str(tmp_path)), \
             patch.object(ingest_module, "Chroma", return_value=store):
            assert ingest_module._collection_is_populated(MagicMock()) is True

    def test_corrupt_store_reports_unpopulated(self, ingest_module, tmp_path):
        """A raising Chroma must fall back to rebuilding rather than crashing startup."""
        with patch.object(ingest_module, "CHROMA_PERSIST_DIR", str(tmp_path)), \
             patch.object(ingest_module, "Chroma", side_effect=RuntimeError("corrupt")):
            assert ingest_module._collection_is_populated(MagicMock()) is False


class TestGetIndexStats:
    def test_reports_count_and_sorted_unique_sources(self, ingest_module):
        store = MagicMock()
        store.get.return_value = {
            "ids": ["1", "2", "3"],
            "metadatas": [{"source": "it_sector"}, {"source": "handbook"}, {"source": "it_sector"}],
        }

        assert ingest_module.get_index_stats(store) == {
            "doc_count": 3,
            "sources": ["handbook", "it_sector"],
        }

    def test_metadata_without_source_becomes_unknown(self, ingest_module):
        store = MagicMock()
        store.get.return_value = {"ids": ["1"], "metadatas": [{}]}

        assert ingest_module.get_index_stats(store)["sources"] == ["unknown"]

    def test_failure_degrades_to_zeroes(self, ingest_module):
        """The UI renders these stats; an exception here must not blank the page."""
        store = MagicMock()
        store.get.side_effect = RuntimeError("connection lost")

        assert ingest_module.get_index_stats(store) == {"doc_count": 0, "sources": []}

    def test_empty_index_reports_zero(self, ingest_module):
        store = MagicMock()
        store.get.return_value = {"ids": [], "metadatas": []}

        assert ingest_module.get_index_stats(store) == {"doc_count": 0, "sources": []}


class TestBuildVectorstore:
    def test_reuses_the_persisted_index_without_embedding(self, ingest_module, tmp_path):
        """The whole point of persistence: no Bedrock embedding spend on restart."""
        existing = MagicMock(name="persisted")

        with patch.object(ingest_module, "_get_embeddings", return_value=MagicMock()), \
             patch.object(ingest_module, "_collection_is_populated", return_value=True), \
             patch.object(ingest_module, "Chroma", return_value=existing) as mock_chroma, \
             patch.object(ingest_module, "_load_documents") as mock_load:
            result = ingest_module.build_vectorstore()

        assert result is existing
        mock_load.assert_not_called()
        mock_chroma.from_documents.assert_not_called()

    def test_builds_from_documents_when_index_is_empty(self, ingest_module):
        built = MagicMock(name="built")

        with patch.object(ingest_module, "_get_embeddings", return_value=MagicMock()), \
             patch.object(ingest_module, "_collection_is_populated", return_value=False), \
             patch.object(ingest_module, "_load_documents", return_value=[MagicMock()]) as mock_load, \
             patch.object(ingest_module, "_split_documents", return_value=[MagicMock()]), \
             patch.object(ingest_module, "Chroma") as mock_chroma:
            mock_chroma.from_documents.return_value = built
            result = ingest_module.build_vectorstore()

        mock_load.assert_called_once()
        mock_chroma.from_documents.assert_called_once()
        assert result is built

    def test_force_rebuild_wipes_the_existing_index(self, ingest_module, tmp_path):
        persist_dir = tmp_path / "chroma_db"
        persist_dir.mkdir()
        (persist_dir / "stale.bin").write_text("old", encoding="utf-8")

        with patch.object(ingest_module, "CHROMA_PERSIST_DIR", str(persist_dir)), \
             patch.object(ingest_module, "_get_embeddings", return_value=MagicMock()), \
             patch.object(ingest_module, "_load_documents", return_value=[MagicMock()]), \
             patch.object(ingest_module, "_split_documents", return_value=[MagicMock()]), \
             patch.object(ingest_module, "Chroma"):
            ingest_module.build_vectorstore(force_rebuild=True)

        assert not persist_dir.exists()

    def test_force_rebuild_skips_the_populated_shortcut(self, ingest_module, tmp_path):
        """Sync must re-embed even when the existing index looks healthy."""
        with patch.object(ingest_module, "CHROMA_PERSIST_DIR", str(tmp_path / "none")), \
             patch.object(ingest_module, "_get_embeddings", return_value=MagicMock()), \
             patch.object(ingest_module, "_collection_is_populated", return_value=True), \
             patch.object(ingest_module, "_load_documents", return_value=[MagicMock()]) as mock_load, \
             patch.object(ingest_module, "_split_documents", return_value=[MagicMock()]), \
             patch.object(ingest_module, "Chroma"):
            ingest_module.build_vectorstore(force_rebuild=True)

        mock_load.assert_called_once()
