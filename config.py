import os
from dotenv import load_dotenv

load_dotenv()

# AWS Bedrock credentials — validated at startup via validate_config()
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
AWS_DEFAULT_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

# Model selection — override via .env
CHAT_MODEL_ID = os.environ.get("CHAT_MODEL_ID", "amazon.nova-pro-v1:0")
EMBEDDING_MODEL_ID = os.environ.get("EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v1")

# Chunking knobs
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "100"))

# Retrieval knobs
RETRIEVAL_K = int(os.environ.get("RETRIEVAL_K", "4"))

# Chroma persistence — relative to the module directory
CHROMA_PERSIST_DIR = os.environ.get(
    "CHROMA_PERSIST_DIR",
    os.path.join(os.path.dirname(__file__), "chroma_db"),
)
CHROMA_COLLECTION_NAME = os.environ.get("CHROMA_COLLECTION_NAME", "it_support")

# Optional LangSmith tracing
LANGSMITH_API_KEY = os.environ.get("LANGSMITH_API_KEY", "")
LANGSMITH_PROJECT = os.environ.get("LANGSMITH_PROJECT", "it-support-chatbot")

# Root directory of this module (used by ingest.py to locate knowledge files)
MODULE_DIR = os.path.dirname(__file__)


def validate_config() -> None:
    """Raise EnvironmentError early if required AWS variables are absent."""
    required = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Add them to a .env file in the project root."
        )

    if LANGSMITH_API_KEY:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_API_KEY
        os.environ["LANGCHAIN_PROJECT"] = LANGSMITH_PROJECT
