import os
from typing import Literal, Optional

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import PromptTemplate
from backend.utils.prompts import CLASSIFY_PROMPT

# Load environment variables from .env if present
load_dotenv()

def classify_request(text: str) -> Literal["CREATE", "MODIFY"]:
    """
    Return 'CREATE' or 'MODIFY' based on the user's input.

    Heuristic rules first; if ambiguous, fallback to Azure OpenAI classification
    (when AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT are set).
    """
    lower = text.lower()

    create_keywords = [
        "create", "new", "design", "build", "setup", "set up",
        "establish", "initialize", "init", "make table", "make schema",
        "define table", "define schema"
    ]

    modify_keywords = [
        "alter", "modify", "change", "update", "drop", "add column",
        "add index", "remove", "delete column", "rename", "truncate",
        "migrate", "refactor schema", "alter table", "drop column",
        "drop index", "rename column", "rename table"
    ]

    # Heuristic: unambiguous create
    if any(k in lower for k in create_keywords) and not any(k in lower for k in modify_keywords):
        return "CREATE"

    # Heuristic: unambiguous modify
    if any(k in lower for k in modify_keywords):
        return "MODIFY"

    # Fallback to LLM
    api_key: Optional[str] = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint: Optional[str] = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment: Optional[str] = os.getenv("AZURE_OPENAI_DEPLOYMENT")

    # If env vars are missing, return a safe default
    if not (api_key and endpoint and deployment):
        return "CREATE"  # safe default

    llm = AzureChatOpenAI(
        api_key=api_key,
        api_version="2024-02-15-preview",
        azure_endpoint=endpoint,
        model=deployment,
        temperature=0,
    )

    prompt = PromptTemplate(input_variables=["text"], template=CLASSIFY_PROMPT)
    resp = llm.invoke(prompt.format(text=text))
    out = (resp.content or "").strip().upper()

    if "MODIFY" in out:
        return "MODIFY"
    return "CREATE"