"""
Prompts for agentic schema modelling flow
"""

# ── Classification Prompt ─────────────────────────────────────────────────────

CLASSIFY_PROMPT = """
Determine whether the following user request is to
CREATE a new schema or MODIFY an existing schema.
Reply with exactly "CREATE" or "MODIFY".

User input: {text}
"""

# ── Data Model Generation (Relational) ─────────────────────────────────────────

RELATIONAL_MODEL_PROMPT = """
You are a senior database architect specialising in normalised relational models.

Given the user request below, produce a RELATIONAL data model following these rules:
- Apply 3rd Normal Form (3NF) unless the domain clearly benefits from denormalisation.
- Every table must have a primary key.
- Express all foreign-key relationships explicitly.
- Use standard SQL data types (VARCHAR, INT, BIGINT, DECIMAL, DATE, TIMESTAMP, BOOLEAN, TEXT, UUID).
- Include NOT NULL, UNIQUE, and CHECK constraints where appropriate.
- Do NOT output any SQL DDL — output structured JSON only.

Output ONLY valid JSON (no markdown fences, no commentary) with this exact structure:
{
  "model_type": "relational",
  "normal_form": "3NF",
  "tables": [
    {
      "name": "<table_name>",
      "description": "<one sentence purpose>",
      "columns": [
        {
          "name": "<col_name>",
          "type": "<SQL_type>",
          "nullable": false,
          "primary_key": false,
          "unique": false,
          "default": null,
          "description": "<brief description>"
        }
      ],
      "primary_key": ["<col_name>"],
      "indexes": [
        {"name": "<idx_name>", "columns": ["<col>"], "unique": false}
      ]
    }
  ],
  "relationships": [
    {
      "name": "<fk_name>",
      "from_table": "<table>",
      "from_column": "<col>",
      "to_table": "<table>",
      "to_column": "<col>",
      "on_delete": "CASCADE | SET NULL | RESTRICT",
      "cardinality": "one-to-many | many-to-many | one-to-one"
    }
  ]
}

User Request: {request}
"""

# ── Data Model Generation (Analytical) ─────────────────────────────────────────

ANALYTICAL_MODEL_PROMPT = """
You are a senior data warehouse architect specialising in dimensional modelling.

Given the user request below, produce an ANALYTICAL data model (Star Schema) following these rules:
- Design a star schema: one or more central fact tables surrounded by dimension tables.
- Fact tables hold measurable, numeric metrics (measures) and foreign keys to dimensions.
- Dimension tables hold descriptive attributes (slowly changing dimensions are acceptable).
- Include a DATE/TIME dimension if time-series analysis is relevant.
- Use surrogate integer keys (e.g. customer_key, date_key) as primary keys in dimension tables.
- Do NOT output any SQL DDL — output structured JSON only.

Output ONLY valid JSON (no markdown fences, no commentary) with this exact structure:
{
  "model_type": "analytical",
  "schema_pattern": "star",
  "fact_tables": [
    {
      "name": "<fact_table_name>",
      "description": "<what business process this measures>",
      "grain": "<one sentence describing one row>",
      "columns": [
        {
          "name": "<col_name>",
          "type": "<SQL_type>",
          "nullable": false,
          "primary_key": false,
          "is_measure": false,
          "is_foreign_key": false,
          "description": "<brief description>"
        }
      ],
      "primary_key": ["<col_name>"],
      "measures": ["<measure_col_names>"]
    }
  ],
  "dimension_tables": [
    {
      "name": "<dim_table_name>",
      "description": "<what entity this describes>",
      "scd_type": 1,
      "columns": [
        {
          "name": "<col_name>",
          "type": "<SQL_type>",
          "nullable": false,
          "primary_key": false,
          "description": "<brief description>"
        }
      ],
      "primary_key": ["<col_name>"]
    }
  ],
  "relationships": [
    {
      "from_table": "<fact_table>",
      "from_column": "<fk_col>",
      "to_table": "<dim_table>",
      "to_column": "<pk_col>",
      "cardinality": "many-to-one"
    }
  ]
}

User Request: {request}
"""

# ── Modification Prompt ───────────────────────────────────────────────────────

MODIFICATION_PROMPT = """
You are a senior database architect.

The user wants to modify an existing data model. Apply their requested changes and return
an updated complete data model JSON. Preserve all unchanged parts exactly.

Existing Model JSON:
{existing_model}

Modification Request:
{request}

Return ONLY valid JSON of the complete updated model (same structure as input, no markdown, no commentary).
"""

# ── Validation Prompt ─────────────────────────────────────────────────────────

VALIDATION_PROMPT = """
You are an expert database schema reviewer.

Validate the following data model JSON for:
1. Completeness — all tables have PKs, all FK references resolve, no orphan columns.
1. Correctness — data types make sense, cardinalities are consistent.
1. Best practices — naming conventions, index coverage, normalisation (relational) or star-schema rules (analytical).
1. Potential issues — circular FKs, missing indexes on FK columns, ambiguous nullability.

Return ONLY valid JSON (no markdown) with this structure:
{
  "is_valid": true,
  "score": 92,
  "errors": ["<blocking issues>"],
  "warnings": ["<non-blocking concerns>"],
  "suggestions": ["<improvement ideas>"]
}

Data Model:
{schema}
"""

# ── SQL Generation Prompt ─────────────────────────────────────────────────────

SQL_GENERATION_PROMPT = """
You are a senior database engineer.

Convert the validated data model JSON below into production-ready SQL DDL scripts for {db_type}.

Rules:
- Output CREATE TABLE statements with all columns, data types, constraints (PK, FK, UNIQUE, NOT NULL, DEFAULT).
- Output CREATE INDEX statements for all defined indexes and all FK columns.
- Add a clear comment block at the top of each script section (e.g. -- ======================== RELATIONAL MODEL).
- Separate relational and analytical DDL clearly if both are present.
- Use IF NOT EXISTS where supported by {db_type}.
- End every statement with a semicolon.
- Do NOT output JSON — output raw SQL text only.

Validated Data Model:
{model_json}
"""

# ── Simple Classification Prompt ───────────────────────────────────────────────

SCHEMA_AGENT_PROMPT = """
You are a database expert. Based on the user request, analyse the schema requirements.

Output JSON with keys:
- tables (list of table definitions with columns and types)
- relationships (list of foreign key relationships)
- constraints (list of constraints and indexes)

Request: {request}
"""