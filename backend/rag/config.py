import os
import logging
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI

# ————————
# LOGGING SETUP
# ————————
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ————————
# ENV LOADING
# ————————
load_dotenv()

AZURE_OPENAI_ENDPOINT             = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY              = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
AZURE_OPENAI_API_VERSION          = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

AZURE_SEARCH_ENDPOINT             = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_API_KEY              = os.getenv("AZURE_SEARCH_API_KEY")

# Required environment variables
_REQUIRED_ENV = [
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
    "AZURE_SEARCH_ENDPOINT",
    "AZURE_SEARCH_API_KEY",
]

_missing = [k for k in _REQUIRED_ENV if not os.getenv(k)]
if _missing:
    raise EnvironmentError(f"Missing required environment variables: {_missing}")

# ————————
# INDEX NAMES
# ————————
SQL_INDEX = "sql-docs-index"
BP_INDEX  = "best-practices-index"

# ————————
# CLIENTS
# ————————
openai_client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

credential = AzureKeyCredential(AZURE_SEARCH_API_KEY)