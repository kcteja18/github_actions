"""Shared fixtures.

Nothing in this suite may reach AWS Bedrock, Chroma, or the network. Modules
are imported lazily inside fixtures/tests so that importing a module never
triggers a live client construction at collection time.
"""
import os
import sys

import pytest

# Modules live at the repo root, not in a package — put it on sys.path so
# `import config` works the same way it does when Streamlit runs app.py.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REQUIRED_AWS_VARS = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION"]


@pytest.fixture
def aws_env(monkeypatch):
    """Populate the AWS vars validate_config() requires, with dummy values."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-key-id")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret-key")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def no_aws_env(monkeypatch):
    """Strip every AWS var so the missing-config path can be exercised."""
    for var in REQUIRED_AWS_VARS:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def fresh_config(monkeypatch):
    """Reimport config.py so module-level env reads happen under the current env.

    config.py evaluates os.environ at import time, so a monkeypatched variable
    has no effect on an already-imported module. Callers use this to assert on
    the parsed module constants rather than on os.environ directly.
    """
    def _reload():
        import importlib

        import config
        return importlib.reload(config)

    yield _reload

    # Restore the module to a known-good state for later tests. Fixture teardown
    # runs before monkeypatch undoes its setenv calls, so a test that injected an
    # invalid value (e.g. CHUNK_SIZE=not-a-number) would make this reload raise.
    # Clear the parsed-at-import vars directly rather than relying on that order.
    for var in ("CHUNK_SIZE", "CHUNK_OVERLAP", "RETRIEVAL_K"):
        os.environ.pop(var, None)

    import importlib

    import config
    importlib.reload(config)
