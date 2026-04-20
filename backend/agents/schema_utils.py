"""
Schema utilities for LLM interaction, JSON parsing, and namespace handling.
"""

import os
import json
import logging
import re
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

try:
    from backend.rag.azure_rag_setup import get_search_client, build_rag_context_block, upload_custom_kb
    RAG_AVAILABLE = True
except Exception as _rag_import_err:
    RAG_AVAILABLE = False
    get_search_client = lambda *args, **kwargs: None
    build_rag_context_block = lambda *a, **kw: ""
    upload_custom_kb = lambda *a, **kw: None

    import logging as _l
    _l.getLogger(__name__).warning(
        "RAG import failed — %s: %s",
        type(_rag_import_err).__name__,
        _rag_import_err,
    )

load_dotenv()
logger = logging.getLogger(__name__)

# ————————————————————
# LLM Loader
# ————————————————————

def get_llm(temperature: float = 0.1):
    """Get Azure OpenAI LLM instance."""
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

    if not (api_key and endpoint and deployment):
        logger.error("Azure OpenAI credentials not found")
        return None

    return AzureChatOpenAI(
        api_key=api_key,
        api_version="2024-02-15-preview",
        azure_endpoint=endpoint,
        model=deployment,
        temperature=temperature,
    )

# ————————————————————
# JSON Parser
# ————————————————————

def parse_json(raw: str) -> dict:
    """Parse JSON from LLM response, handling various formats."""
    cleaned = raw.strip()

    if "```" in cleaned:
        parts = cleaned.split("```")
        if len(parts) >= 3:
            cleaned = parts[1]

    if cleaned.startswith("json"):
        cleaned = cleaned[4:]

    cleaned = cleaned.strip()

    # Try direct JSON
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON inside braces
    m = re.search(r"{[\s\S]*}", cleaned)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    logger.error("JSON parse failed. Raw (500 chars): %s", raw[:500])
    return {"parse_error": True, "raw": raw}

# ————————————————————
# LLM Invocation Wrapper
# ————————————————————

def invoke_llm(llm, prompt_text: str) -> dict:
    """Invoke LLM and parse JSON response."""
    try:
        response = llm.invoke(prompt_text)
        raw_content = response.content if hasattr(response, 'content') else str(response)
        return parse_json(raw_content)
    except Exception as e:
        logger.error("LLM invocation failed: %s", e)
        return {"parse_error": True, "error": str(e)}

# ————————————————————
# Namespace Extraction
# ————————————————————

def extract_namespace(request: str, db_type: str) -> dict:
    """Extract namespace information from request for BigQuery."""
    result = {}

    if db_type == "BigQuery":
        # Look for project.dataset patterns
        patterns = [
            r'project[:\s]+([a-zA-Z0-9_-]+)',
            r'dataset[:\s]+([a-zA-Z0-9_-]+)',
            r'([a-zA-Z0-9_-]+)\.([a-zA-Z0-9_-]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, request, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:
                    result['project'] = match.group(1)
                    result['dataset'] = match.group(2)
                break

        # Default fallback
        if not result:
            result = {"project": "my_project", "dataset": "ecommerce"}

    else:
        # For other databases, look for schema patterns
        schema_patterns = [
            r'schema[:\s]+([a-zA-Z0-9_-]+)',
            r'database[:\s]+([a-zA-Z0-9_-]+)',
        ]

        for pattern in schema_patterns:
            match = re.search(pattern, request, re.IGNORECASE)
            if match:
                result['schema'] = match.group(1)
                break

    logger.info("Extracted namespace for %s: %s", db_type, result)
    return result

# ————————————————————
# Namespace Stamping
# ————————————————————

def stamp_namespace(model: dict, namespace: dict, db_type: str) -> dict:
    """Apply namespace prefixes to table names."""
    if not namespace or not model or model.get("parse_error"):
        return model

    def prefix(table_name: str) -> str:
        if db_type == "BigQuery" and 'project' in namespace and 'dataset' in namespace:
            return f"{namespace['project']}.{namespace['dataset']}.{table_name}"
        elif 'schema' in namespace:
            return f"{namespace['schema']}.{table_name}"
        return table_name

    def patch_tables(table_list: list) -> list:
        if not table_list:
            return table_list
        return [{**t, 'name': prefix(t['name'])} for t in table_list]

    def patch_relationships(rel_list: list) -> list:
        if not rel_list:
            return rel_list
        patched = []
        for r in rel_list:
            new_r = dict(r)
            if 'from_entity' in r:
                new_r['from_entity'] = prefix(r['from_entity'])
                new_r['to_entity'] = prefix(r['to_entity'])
            elif 'from_table' in r:
                new_r['from_table'] = prefix(r['from_table'])
                new_r['to_table'] = prefix(r['to_table'])
            patched.append(new_r)
        return patched

    model = dict(model)

    for key in ("tables", "fact_tables", "dimension_tables"):
        if key in model:
            model[key] = patch_tables(model[key])

    if "relationships" in model:
        model["relationships"] = patch_relationships(model["relationships"])

    model["namespace"] = namespace
    return model

# ════════════════════════════════════════════════════════════════
# CUSTOM KB CONTEXT BUILDER
# ════════════════════════════════════════════════════════════════

def build_custom_kb_context(request: str, custom_kb: dict, top_k: int = 3) -> str:
    """
    Build RAG context from custom knowledge base JSON.
    Similar to build_rag_context_block but searches the provided dict.
    """
    if not custom_kb:
        return ""

    entries = custom_kb.get("entries", [])
    if not entries:
        return ""

    logger.info("Custom KB loaded with %d entries", len(entries))

    # Extract keywords from request (words > 4 chars)
    keywords = [w.lower() for w in request.split() if len(w) > 4]
    if not keywords:
        # Fallback: take first few entries
        selected = entries[:top_k]
    else:
        # Score entries based on keyword matches
        scored = []
        for entry in entries:
            field_name = entry.get("field_name", "").lower()
            desc = entry.get("professional_description", "").lower()
            score = sum(1 for kw in keywords if kw in field_name or kw in desc)
            scored.append((score, entry))
        scored.sort(reverse=True, key=lambda x: x[0])
        selected = [entry for score, entry in scored[:top_k] if score > 0]
        if not selected:
            selected = entries[:top_k]

    parts = []
    for entry in selected:
        field = entry.get("field_name", "")
        desc = entry.get("professional_description", "")
        constraints = entry.get("constraints", "")
        related = entry.get("related_fields", "")
        compliance = entry.get("compliance_notes", "")

        part = f"Reference Field : {field}\nDescription     : {desc}"
        if constraints:
            part += f"\nConstraints     : {constraints}"
        if related:
            part += f"\nRelated Fields  : {related}"
        if compliance:
            part += f"\nCompliance      : {compliance}"
        parts.append(part)

    if not parts:
        return ""

    logger.info("Extracted %d relevant entries from custom KB", len(parts))

    separator = "\n\n---\n\n"
    context = (
        "=== CUSTOM KNOWLEDGE BASE CONTEXT ===\n"
        "Use these professional field descriptions.\n\n"
        + separator.join(parts)
        + "\n=== END CUSTOM CONTEXT ==="
    )

    logger.info("Custom KB context built (%d chars)", len(context))
    return context