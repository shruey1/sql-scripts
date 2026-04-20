"""
Logical model generation agent.
"""

import logging
from typing import Optional, Dict
from .schema_utils import get_llm, invoke_llm

logger = logging.getLogger(__name__)

# ————————————————————
# Logical Model Prompt
# ————————————————————

def _logical_prompt(request: str, model_type: str = "relational") -> str:
    """Generate prompt for logical model creation."""
    model_hint = ""
    if model_type == "relational":
        model_hint = "Focus on normalized relational structures."
    elif model_type == "analytical":
        model_hint = "Include analytical structures like fact and dimension tables."

    return f"""
You are a senior data architect. Given a business description, produce a
LOGICAL data model — engine-agnostic, no physical types, no DDL.

{model_hint}

Output ONLY valid JSON:
{{
  "model_type": "logical",
  "entities": [
    {{
      "name": "EntityName",
      "description": "What this entity represents",
      "attributes": [
        {{
          "name": "attribute_name",
          "description": "What this attribute stores",
          "is_identifier": true,
          "is_required": true
        }}
      ]
    }}
  ],
  "relationships": [
    {{
      "from_entity": "EntityA",
      "to_entity": "EntityB",
      "label": "places",
      "cardinality": "many-to-one"
    }}
  ]
}}

Rules:
1. No SQL types — use plain English concepts (identifier, text, number, date, boolean, amount)
2. Every entity and attribute MUST have a description
3. Mark exactly one attribute per entity as "is_identifier": true
4. Keep it business-facing, not technical
5. Use business-friendly names for entities and attributes. Avoid snake_case, underscores, and technical abbreviations. Prefer natural language naming like Customer, Order Date, Product Category.

User Request: {request}
"""

def create_logical_model(
    request: str,
    db_engine: str = "MySQL",
    model_type: str = "relational",
    custom_kb: dict | None = None
) -> dict:
    """Create a logical data model from business requirements."""
    llm = get_llm()
    if not llm:
        return {"parse_error": True, "error": "LLM not available"}

    prompt = _logical_prompt(request, model_type)
    result = invoke_llm(llm, prompt)

    if result.get("parse_error"):
        logger.error("Logical model generation failed")
        return result

    # Add metadata
    result["db_type"] = db_engine
    result["model_type"] = model_type

    return result