"""Tests for config.py — env parsing and startup validation."""
import os

import pytest


class TestValidateConfig:
    def test_passes_when_all_aws_vars_present(self, aws_env):
        import config

        config.validate_config()  # must not raise

    def test_raises_when_all_aws_vars_missing(self, no_aws_env):
        import config

        with pytest.raises(EnvironmentError) as exc:
            config.validate_config()

        message = str(exc.value)
        assert "AWS_ACCESS_KEY_ID" in message
        assert "AWS_SECRET_ACCESS_KEY" in message
        assert "AWS_DEFAULT_REGION" in message

    @pytest.mark.parametrize(
        "missing_var",
        ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION"],
    )
    def test_raises_naming_the_one_missing_var(self, aws_env, monkeypatch, missing_var):
        """A partial config must fail, and the error must name the culprit."""
        import config

        monkeypatch.delenv(missing_var)

        with pytest.raises(EnvironmentError, match=missing_var):
            config.validate_config()

    def test_empty_string_counts_as_missing(self, aws_env, monkeypatch):
        """A blank value is not a usable credential — it must be rejected."""
        import config

        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "")

        with pytest.raises(EnvironmentError, match="AWS_ACCESS_KEY_ID"):
            config.validate_config()

    def test_langsmith_tracing_enabled_when_key_present(self, aws_env, monkeypatch, fresh_config):
        monkeypatch.setenv("LANGSMITH_API_KEY", "ls-test-key")
        monkeypatch.setenv("LANGSMITH_PROJECT", "test-project")
        for var in ("LANGCHAIN_TRACING_V2", "LANGCHAIN_API_KEY", "LANGCHAIN_PROJECT"):
            monkeypatch.delenv(var, raising=False)

        cfg = fresh_config()
        cfg.validate_config()

        assert os.environ["LANGCHAIN_TRACING_V2"] == "true"
        assert os.environ["LANGCHAIN_API_KEY"] == "ls-test-key"
        assert os.environ["LANGCHAIN_PROJECT"] == "test-project"

    def test_langsmith_tracing_untouched_when_key_absent(self, aws_env, monkeypatch, fresh_config):
        monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
        monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)

        cfg = fresh_config()
        cfg.validate_config()

        assert "LANGCHAIN_TRACING_V2" not in os.environ


class TestConfigDefaults:
    def test_defaults_apply_when_env_unset(self, monkeypatch, fresh_config):
        for var in (
            "CHAT_MODEL_ID", "EMBEDDING_MODEL_ID", "CHUNK_SIZE",
            "CHUNK_OVERLAP", "RETRIEVAL_K", "CHROMA_COLLECTION_NAME",
            "AWS_DEFAULT_REGION",
        ):
            monkeypatch.delenv(var, raising=False)

        cfg = fresh_config()

        assert cfg.CHAT_MODEL_ID == "amazon.nova-pro-v1:0"
        assert cfg.EMBEDDING_MODEL_ID == "amazon.titan-embed-text-v1"
        assert cfg.AWS_DEFAULT_REGION == "us-east-1"
        assert cfg.CHUNK_SIZE == 500
        assert cfg.CHUNK_OVERLAP == 100
        assert cfg.RETRIEVAL_K == 4
        assert cfg.CHROMA_COLLECTION_NAME == "it_support"

    def test_env_overrides_are_honoured(self, monkeypatch, fresh_config):
        monkeypatch.setenv("CHAT_MODEL_ID", "custom.model-v2")
        monkeypatch.setenv("CHUNK_SIZE", "1200")
        monkeypatch.setenv("RETRIEVAL_K", "8")

        cfg = fresh_config()

        assert cfg.CHAT_MODEL_ID == "custom.model-v2"
        assert cfg.CHUNK_SIZE == 1200
        assert cfg.RETRIEVAL_K == 8

    def test_numeric_knobs_are_ints_not_strings(self, fresh_config):
        """These feed splitter/retriever kwargs — a str would fail deep in LangChain."""
        cfg = fresh_config()

        assert isinstance(cfg.CHUNK_SIZE, int)
        assert isinstance(cfg.CHUNK_OVERLAP, int)
        assert isinstance(cfg.RETRIEVAL_K, int)

    def test_non_numeric_chunk_size_fails_loudly_at_import(self, monkeypatch, fresh_config):
        """Better a hard ValueError at startup than a confusing failure mid-ingest."""
        monkeypatch.setenv("CHUNK_SIZE", "not-a-number")

        with pytest.raises(ValueError):
            fresh_config()

    def test_overlap_smaller_than_chunk_size(self, fresh_config):
        """Overlap >= size makes RecursiveCharacterTextSplitter raise."""
        cfg = fresh_config()

        assert cfg.CHUNK_OVERLAP < cfg.CHUNK_SIZE

    def test_persist_dir_is_absolute(self, fresh_config):
        """Must not depend on CWD — Streamlit and pytest run from different dirs."""
        cfg = fresh_config()

        assert os.path.isabs(cfg.CHROMA_PERSIST_DIR)
