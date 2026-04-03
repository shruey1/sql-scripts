"""
Agent responsible for validating JSON data models.
"""

import os
import json
import re
import logging
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

load_dotenv()

logger = logging.getLogger(__name__)


def _get_llm():
    api_key    = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint   = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

    if not (api_key and endpoint and deployment):
        return None

    return AzureChatOpenAI(
        api_key=api_key,
        api_version="2024-02-15-preview",
        azure_endpoint=endpoint,
        model=deployment,
        temperature=0,
    )


def _parse_json(raw: str) -> dict | None:
    """
    Robustly extract a JSON object from an LLM response.
    Handles: markdown fences, leading/trailing text, stray whitespace.
    """
    if not raw:
        return None

    # 1. Try direct parse
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass

    # 2. Try to extract ```json ... ```
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3. Try any {...} block
    brace_match = re.search(r"\{[\s\S]*\}", raw)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    logger.error(
        "Could not parse validation JSON. Raw (first 500):\n%s", raw[:500]
    )
    return None


class ValidationAgent:
    def __init__(self):
        self.llm = _get_llm()

    def validate_model(self, model: dict) -> dict:
        if not self.llm:
            return self._basic_validation(model)

        prompt = f"""
You are an expert database schema reviewer.

Validate the following data model JSON for:
1. Completeness — all tables have PKs, all FK references resolve, no orphan columns.
2. Correctness — data types make sense, cardinalities are consistent.
3. Best practices — naming conventions, index coverage, normalisation rules.
4. Potential issues — circular FKs, missing indexes on FK columns, ambiguous nullability.

You MUST respond with ONLY a valid JSON object — no markdown fences, no explanation, no preamble.

The JSON must have exactly these keys:
{{
  "is_valid": true,
  "score": 85,
  "errors": [],
  "warnings": ["example warning"],
  "suggestions": ["example suggestion"]
}}

Data Model to validate:
{json.dumps(model, indent=2)}
"""

        try:
            resp = self.llm.invoke(prompt)
            raw = resp.content

            logger.info("Validation raw response (first 300): %s", raw[:300])

            parsed = _parse_json(raw)
            if parsed is None:
                logger.warning("Falling back to basic validation — could not parse LLM response")
                return self._basic_validation(model)

            # Normalize keys and types
            parsed["is_valid"]    = bool(parsed.get("is_valid", True))
            parsed["score"]       = int(parsed.get("score", 100 if parsed["is_valid"] else 50))
            parsed["errors"]      = list(parsed.get("errors", []))
            parsed["warnings"]    = list(parsed.get("warnings", []))
            parsed["suggestions"] = list(parsed.get("suggestions", []))

            return parsed

        except Exception as e:
            logger.error("Validation LLM error: %s", e)
            return self._basic_validation(model)

    def _basic_validation(self, model: dict) -> dict:
        errors, warnings, suggestions = [], [], []

        if not isinstance(model, dict):
            return {
                "is_valid": False,
                "score": 0,
                "errors": ["Model must be a JSON object"],
                "warnings": [],
                "suggestions": []
            }

        rel  = model.get("relational_model")
        anal = model.get("analytical_model")

        # If neither key exists, treat as flat model
        if not rel and not anal:
            if model.get("model_type") == "relational":
                rel = model
            elif model.get("model_type") == "analytical":
                anal = model

        if rel:
            tables = rel.get("tables", [])
            if not tables:
                errors.append("Relational model has no tables.")

            for t in tables:
                if not t.get("primary_key"):
                    errors.append(f"Table '{t.get('name')}' has no primary key.")

                for col in t.get("columns", []):
                    if not col.get("type"):
                        errors.append(
                            f"Column '{col.get('name')}' in '{t.get('name')}' has no type."
                        )

        if anal:
            if not anal.get("fact_tables"):
                errors.append("Analytical model has no fact tables.")

            if not anal.get("dimension_tables"):
                warnings.append("Analytical model has no dimension tables.")

        score = max(0, 100 - len(errors) * 20 - len(warnings) * 5)

        return {
            "is_valid":    len(errors) == 0,
            "score":       score,
            "errors":      errors,
            "warnings":    warnings,
            "suggestions": suggestions,
        }


def validate_model(model: dict) -> dict:
    return ValidationAgent().validate_model(model)