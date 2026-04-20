"""
Physical model generation agent (relational and analytical).
"""

import json
import logging
from typing import Optional, Dict
from .schema_utils import get_llm, invoke_llm, extract_namespace, stamp_namespace, build_custom_kb_context
from .scd_agent import apply_scd_to_dimension

logger = logging.getLogger(__name__)

# ————————————————————
# Engine-Specific Hints
# ————————————————————

def _engine_hints(db_type: str) -> str:
    """Get database-specific DDL hints and rules."""
    hints = {
        "BigQuery": """
Engine-specific rules for BigQuery:
- Use BigQuery native types ONLY: STRING, INT64, FLOAT64, NUMERIC, BIGNUMERIC, BOOL, DATE, DATETIME, TIMESTAMP, TIME, BYTES, JSON, ARRAY<T>, STRUCT<…>, GEOGRAPHY.
- Do NOT use VARCHAR, INT, INTEGER, FLOAT, BOOLEAN, TEXT, SERIAL, AUTO_INCREMENT, IDENTITY.
- All PRIMARY KEY and FOREIGN KEY constraints MUST include NOT ENFORCED.
- Fully qualified table names: project.dataset.table_name.
- BigQuery does NOT support CREATE INDEX — omit entirely.
- No ON DELETE CASCADE — foreign keys are informational only.
""",
        "PostgreSQL": """
Engine-specific rules for PostgreSQL:
- Preferred types: TEXT, VARCHAR(n), INTEGER, BIGINT, SMALLINT, BOOLEAN, JSONB, UUID, TIMESTAMPTZ, TIMESTAMP, DATE, NUMERIC(p,s), BYTEA, SERIAL (legacy), BIGSERIAL (legacy).
- For auto-increment use: col_name INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY
- Supports UNIQUE, CHECK, composite PKs, partial indexes, and ON DELETE CASCADE.
""",
        "MySQL": """
Engine-specific rules for MySQL / MariaDB:
- Use: VARCHAR(n), CHAR(n), TEXT, MEDIUMTEXT, LONGTEXT, INT, BIGINT, SMALLINT, TINYINT,
  DECIMAL(p,s), FLOAT, DOUBLE, TINYINT(1) for BOOLEAN, DATE, DATETIME(6), TIMESTAMP(6), JSON.
- Auto-increment PK: col_name INT NOT NULL AUTO_INCREMENT PRIMARY KEY.
- Default storage engine: ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci.
""",
        # Add other database hints as needed
    }
    return hints.get(db_type, f"\nUse standard SQL data types and constraints appropriate for {db_type}.\n")

# ————————————————————
# Relational Model Generation
# ————————————————————

def _relational_prompt(
    request: str,
    db_type: str,
    rag_context: str = "",
    logical_model: dict | None = None
) -> str:
    """Generate prompt for relational model creation."""
    rag_block = f"\n{rag_context}\n" if rag_context else ""

    logical_block = ""
    if logical_model and not logical_model.get("error"):
        entities = logical_model.get("entities", [])
        entity_count = len(entities)
        entity_names = [e.get("name", "") for e in entities]

        logical_block = f"""
LOGICAL DATA MODEL (AUTHORITATIVE SOURCE) — {entity_count} ENTITIES TOTAL:
{json.dumps(logical_model, indent=2)}

CRITICAL CONSTRAINTS:
- Build upon the {entity_count} entities: {', '.join(entity_names)}
- Create exactly {entity_count} tables (one per entity)
- Preserve ALL attributes as columns
- Convert relationships to foreign keys
"""

    return f"""
You are a senior database architect specialising in 3NF relational models.
{rag_block}
{logical_block}

Target database: {db_type}
{_engine_hints(db_type)}

Output ONLY valid JSON:
{{
  "model_type": "relational",
  "db_type": "{db_type}",
  "tables": [
    {{
      "name": "example_table",
      "description": "Stores …",
      "columns": [
        {{
          "name": "id",
          "type": "…",
          "nullable": false,
          "description": "Primary key"
        }}
      ]
    }}
  ],
  "relationships": [],
  "indexes": []
}}

User Request: {request}
"""

def create_relational_model(
    request: str,
    db_type: str,
    logical_model: dict | None = None,
    custom_kb: dict | None = None
) -> dict:
    """Create a relational physical model."""
    llm = get_llm()
    if not llm:
        return {"parse_error": True, "error": "LLM not available"}

    # Build context
    rag_context = build_custom_kb_context(request, custom_kb) if custom_kb else ""
    namespace = extract_namespace(request, db_type)

    prompt = _relational_prompt(request, db_type, rag_context, logical_model)
    result = invoke_llm(llm, prompt)

    if result.get("parse_error"):
        logger.error("Relational model generation failed")
        return result

    # Apply namespace
    result = stamp_namespace(result, namespace, db_type)

    # Add metadata
    result["normal_form"] = "3NF"

    return result

# ————————————————————
# Analytical Model Generation
# ————————————————————

def _analytical_prompt(
    request: str,
    db_type: str,
    rag_context: str = "",
    logical_model: dict | None = None
) -> str:
    """Generate prompt for analytical model creation."""
    rag_block = f"\n{rag_context}\n" if rag_context else ""

    logical_block = ""
    if logical_model and not logical_model.get("error"):
        entities = logical_model.get("entities", [])
        entity_count = len(entities)
        entity_names = [e.get("name", "") for e in entities]

        logical_block = f"""
LOGICAL DATA MODEL (AUTHORITATIVE SOURCE) — {entity_count} ENTITIES TOTAL:
{json.dumps(logical_model, indent=2)}

CRITICAL CONSTRAINTS:
- Build star schema upon the {entity_count} entities: {', '.join(entity_names)}
- Identify FACT tables from transactional entities
- Identify DIMENSION tables from descriptive entities
- Apply appropriate SCD types to dimensions
"""

    scd_rules = """
SCD (Slowly Changing Dimension) type selection rules:
- SCD Type 0: Static/never changes
- SCD Type 1: Overwrite old value
- SCD Type 2: Add new row with effective/expiry dates and is_current flag
- SCD Type 3: Track only one previous value (add prev_<col> column)
- SCD Type 4: Separate history table
- SCD Type 6: Hybrid of Type 1 + 2 + 3
"""

    return f"""
You are a senior data warehouse architect specialising in STAR SCHEMA modelling.
{rag_block}
{logical_block}

Target: {db_type}
{_engine_hints(db_type)}
{scd_rules}

Output ONLY valid JSON:
{{
  "model_type": "analytical",
  "schema_pattern": "star",
  "db_type": "{db_type}",
  "fact_tables": [],
  "dimension_tables": [],
  "relationships": []
}}

User Request: {request}
"""

def create_analytical_model(
    request: str,
    db_type: str,
    logical_model: dict | None = None,
    custom_kb: dict | None = None
) -> dict:
    """Create an analytical physical model with SCD."""
    llm = get_llm()
    if not llm:
        return {"parse_error": True, "error": "LLM not available"}

    # Build context
    rag_context = build_custom_kb_context(request, custom_kb) if custom_kb else ""
    namespace = extract_namespace(request, db_type)

    prompt = _analytical_prompt(request, db_type, rag_context, logical_model)
    result = invoke_llm(llm, prompt)

    if result.get("parse_error"):
        logger.error("Analytical model generation failed")
        return result

    # Apply SCD to dimension tables
    if "dimension_tables" in result:
        result["dimension_tables"] = [
            apply_scd_to_dimension(dim) for dim in result["dimension_tables"]
        ]

    # Apply namespace
    result = stamp_namespace(result, namespace, db_type)

    return result

# ————————————————————
# Modification Prompt
# ————————————————————

def _modification_prompt(existing_model: dict, request: str) -> str:
    """Generate prompt for model modification."""
    return f"""
You are a senior database architect.

Modify this existing model based on the request:
{json.dumps(existing_model, indent=2)}

Request: {request}

Output the modified model in the same JSON format.
"""

def modify_physical_model(existing_model: dict, request: str, db_type: str) -> dict:
    """Modify an existing physical model."""
    llm = get_llm()
    if not llm:
        return {"parse_error": True, "error": "LLM not available"}

    prompt = _modification_prompt(existing_model, request)
    result = invoke_llm(llm, prompt)

    if result.get("parse_error"):
        logger.error("Model modification failed")
        return result

    return result