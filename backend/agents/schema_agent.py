"""
Agent responsible for generating structured JSON data models.
"""

import os
import json
import logging
import re
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

try:
    from backend.rag.azure_rag_setup import get_search_client,  build_rag_context_block
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    get_search_client = lambda: None
    build_rag_context_block = lambda: None


load_dotenv()

logger = logging.getLogger(__name__)

# ————————————————————
# LLM Loader
# ————————————————————

def _get_llm(temperature: float = 0.1):
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

def _parse_json(raw: str) -> dict:
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

def _invoke_llm(llm, prompt_text: str) -> dict:
    try:
        resp = llm.invoke(prompt_text)
        result = _parse_json(resp.content)

        if isinstance(result, dict):
            logger.info("LLM response keys: %s", list(result.keys()))
        else:
            logger.info("LLM response type: %s", type(result))

        return result

    except Exception as e:
        logger.error("LLM error: %s", e)
        return {"error": str(e)}

# ————————————————————
# Namespace Extraction
# ————————————————————

def _extract_namespace(request: str, db_type: str) -> dict:

    result = {}

    if db_type == "BigQuery":

        # Only backtick-qualified: `project.dataset`

        m = re.search(r'`([\w-]+)\.([\w-]+)(?:\.[\w-]+)?`', request)

        if m:

            result["project"] = m.group(1)

            result["dataset"] = m.group(2)

        else:

            # Only explicit colon syntax: project: foo  dataset: bar

            pm = re.search(r'\bproject\s*:\s*([\w-]+)', request, re.IGNORECASE)

            dm = re.search(r'\bdataset\s*:\s*([\w-]+)', request, re.IGNORECASE)

            if pm:

                result["project"] = pm.group(1)

            if dm:

                result["dataset"] = dm.group(1)

    else:

        # Only explicit colon syntax: schema: foo  OR  database: foo

        # NEVER infer from plain English words like "schema for e-commerce"

        sm = re.search(r'\b(?:schema|database|db)\s*:\s*([\w-]+)', request, re.IGNORECASE)

        if sm:

            result["schema"] = sm.group(1)

    logger.info("Extracted namespace for %s: %s", db_type, result)

    return result
 
 

# ————————————————————
# Namespace Stamping
# ————————————————————

def _stamp_namespace(model: dict, namespace: dict, db_type: str) -> dict:

    if not namespace or not model or model.get("parse_error"):
        return model

    def _prefix(table_name: str) -> str:
        if "." in table_name:
            return table_name

        if db_type == "BigQuery":
            project = namespace.get("project", "")
            dataset = namespace.get("dataset", "")

            if project and dataset:
                return f"{project}.{dataset}.{table_name}"
            if dataset:
                return f"{dataset}.{table_name}"

        else:  # SQL / Warehouse
            schema = namespace.get("schema", "")
            if schema:
                return f"{schema}.{table_name}"

        return table_name

    def _patch_tables(table_list: list) -> list:
        return [{**t, "name": _prefix(t["name"])} for t in table_list]

    def _patch_relationships(rel_list: list) -> list:
        return [
            {
                **r,
                "from_table": _prefix(r["from_table"]),
                "to_table": _prefix(r["to_table"])
            }
            for r in rel_list
        ]

    model = dict(model)

    for key in ("tables", "fact_tables", "dimension_tables"):
        if key in model:
            model[key] = _patch_tables(model[key])

    if "relationships" in model:
        model["relationships"] = _patch_relationships(model["relationships"])

    model["namespace"] = namespace
    return model
# ————————————————————
# Engine-Specific Hints  (FIX #5 — full DDL reference syntax per engine)
# ————————————————————

def _engine_hints(db_type: str) -> str:
    hints = {
        "BigQuery": """
Engine-specific rules for BigQuery:
- Use BigQuery native types ONLY: STRING, INT64, FLOAT64, NUMERIC, BIGNUMERIC, BOOL, DATE, DATETIME, TIMESTAMP, TIME, BYTES, JSON, ARRAY<T>, STRUCT<…>, GEOGRAPHY.
- Do NOT use VARCHAR, INT, INTEGER, FLOAT, BOOLEAN, TEXT, SERIAL, AUTO_INCREMENT, IDENTITY.
- All PRIMARY KEY and FOREIGN KEY constraints MUST include NOT ENFORCED.
- Fully qualified table names: project.dataset.table_name.
- BigQuery does NOT support CREATE INDEX — omit entirely.
- No ON DELETE CASCADE — foreign keys are informational only.

Reference DDL syntax for BigQuery:
CREATE [ OR REPLACE ] [ TEMP | TEMPORARY ] TABLE [ IF NOT EXISTS ]
table_name
[
(
column_name column_type [ NOT NULL ] [ DEFAULT expr ] [ OPTIONS(…) ]
[, …]
[, PRIMARY KEY (column_name [, …]) NOT ENFORCED ]
[, CONSTRAINT constraint_name
  FOREIGN KEY (column_name [, …])
  REFERENCES primary_key_table (column_name [, …]) NOT ENFORCED ]
)
]
[ DEFAULT COLLATE collate_specification ]
[ PARTITION BY partition_expression ]
[ CLUSTER BY clustering_column_list ]
[ OPTIONS( table_option_list ) ]
[ AS query_statement ]
""",

        "PostgreSQL": """
Engine-specific rules for PostgreSQL:
- Preferred types: TEXT, VARCHAR(n), INTEGER, BIGINT, SMALLINT, BOOLEAN, JSONB, UUID, TIMESTAMPTZ, TIMESTAMP, DATE, NUMERIC(p,s), BYTEA, SERIAL (legacy), BIGSERIAL (legacy).
- For auto-increment use: col_name INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY
- Supports UNIQUE, CHECK, composite PKs, partial indexes, and ON DELETE CASCADE.
- Use JSONB instead of JSON unless ordering of keys matters.

Reference DDL syntax for PostgreSQL:
CREATE [ [ GLOBAL | LOCAL ] { TEMPORARY | TEMP } | UNLOGGED ] TABLE
[ IF NOT EXISTS ] table_name (
  column_name data_type
  [ COLLATE collation ]
  [ column_constraint [ … ] ]
  [, …]
  [, table_constraint ]
  [, LIKE source_table [ like_option … ] ]
)
[ INHERITS ( parent_table [, …] ) ]
[ PARTITION BY { RANGE | LIST | HASH } ( { column_name | ( expression ) } ) ]
[ TABLESPACE tablespace_name ]

column_constraint:
[ CONSTRAINT constraint_name ]
{ NOT NULL | NULL | DEFAULT expr | GENERATED ALWAYS AS IDENTITY |
  UNIQUE [ NULLS [ NOT ] DISTINCT ] |
  PRIMARY KEY |
  CHECK ( expression ) |
  REFERENCES reftable [ ( refcolumn ) ]
  [ ON DELETE { NO ACTION | RESTRICT | CASCADE | SET NULL | SET DEFAULT } ] }

CREATE [ UNIQUE ] INDEX [ CONCURRENTLY ] [ name ] ON [ ONLY ] table_name
[ USING method ] ( { column_name | ( expression ) } [, …] )
[ WHERE predicate ]
""",

        "MSSQL": """
Engine-specific rules for SQL Server:
- Use: NVARCHAR(n), NVARCHAR(MAX), NCHAR(n), INT, BIGINT, SMALLINT, TINYINT, BIT, DECIMAL(p,s),
  FLOAT, REAL, MONEY, DATETIME2(n), DATE, TIME(n), DATETIMEOFFSET, UNIQUEIDENTIFIER, VARBINARY(MAX), XML.
- Auto-increment: col_name INT IDENTITY(1,1) NOT NULL PRIMARY KEY.
- Avoid deprecated TEXT, NTEXT, IMAGE types.
- Supports UNIQUE, CHECK, indexes, and ON DELETE CASCADE / SET NULL.

Reference DDL syntax for SQL Server:
CREATE TABLE [ database_name . [ schema_name ] . | schema_name . ] table_name (
  column_name data_type
  [ NULL | NOT NULL ]
  [ DEFAULT constant_expression ]
  [ IDENTITY [ ( seed , increment ) ] ]
  [ ROWGUIDCOL ]
  [ column_constraint [ …n ] ]
  [, …]
  [, table_constraint [ …n ] ]
)
[ ON { partition_scheme_name ( column_name ) | filegroup | "default" } ]

column_constraint / table_constraint:
[ CONSTRAINT constraint_name ]
{ PRIMARY KEY | UNIQUE } [ CLUSTERED | NONCLUSTERED ]
( column_name [ ASC | DESC ] [, …n] )
| CHECK ( logical_expression )
| FOREIGN KEY ( column_name [, …n] )
  REFERENCES ref_table [ ( ref_column [, …n] ) ]
  [ ON DELETE { NO ACTION | CASCADE | SET NULL | SET DEFAULT } ]

CREATE [ UNIQUE ] [ CLUSTERED | NONCLUSTERED ] INDEX index_name
ON table_name ( column [, …] )
[ INCLUDE ( column [, …] ) ]
[ WHERE filter_predicate ]
""",

        "Snowflake": """
Engine-specific rules for Snowflake:
- Supported types: VARCHAR(n), STRING, CHAR(n), NUMBER(p,s), INT, BIGINT, FLOAT, BOOLEAN,
  DATE, TIMESTAMP_NTZ(n), TIMESTAMP_LTZ(n), TIMESTAMP_TZ(n), VARIANT, ARRAY, OBJECT, GEOGRAPHY.
- PK/FK constraints are accepted but NOT enforced by default.
- Surrogate keys: col_name NUMBER AUTOINCREMENT PRIMARY KEY or IDENTITY(1,1).
- Do NOT generate CREATE INDEX — Snowflake does not support it.
- Use CLUSTER BY for micro-partition clustering.

Reference DDL syntax for Snowflake:
CREATE [ OR REPLACE ] [ { [ LOCAL | GLOBAL ] TEMPORARY | VOLATILE | TRANSIENT } ]
TABLE [ IF NOT EXISTS ] <table_name> (
  <col_name> <col_type>
    [ NOT NULL ] [ DEFAULT <expr> | AUTOINCREMENT | IDENTITY (seed, step) ]
    [ UNIQUE | PRIMARY KEY ]
    [ REFERENCES <ref_table> ( <ref_col> ) ]
    [ COMMENT '<string>' ]
  [, …]
  [, PRIMARY KEY ( <col_name> [, …] ) ]
  [, [ CONSTRAINT <name> ] FOREIGN KEY ( <col_name> [, …] )
       REFERENCES <ref_table> ( <col_name> [, …] )
       [ NOT ENFORCED ] ]
)
[ CLUSTER BY ( <expr> [, …] ) ]
[ DATA_RETENTION_TIME_IN_DAYS = <n> ]
[ COMMENT = '<string>' ]
""",

        "SQLite": """
Engine-specific rules for SQLite:
- SQLite storage classes: TEXT, INTEGER, REAL, BLOB, NUMERIC.
- BOOLEAN → INTEGER (0/1). DATETIME → TEXT or INTEGER epoch.
- Auto-increment PK: col_name INTEGER PRIMARY KEY.
- Foreign key enforcement requires PRAGMA foreign_keys = ON.
- No ALTER COLUMN/DROP COLUMN in older versions.

Reference DDL syntax for SQLite:
CREATE [ TEMP | TEMPORARY ] TABLE [ IF NOT EXISTS ]
[ schema_name . ] table_name (
  column_def [, …]
  [, table_constraint ]*
) [ WITHOUT ROWID ]

column_def:
  column_name [ type_name ]
  [ NOT NULL [ conflict_clause ] ]
  [ DEFAULT (expr) | DEFAULT literal ]
  [ PRIMARY KEY [ ASC | DESC ] [ conflict_clause ] [ AUTOINCREMENT ] ]
  [ UNIQUE [ conflict_clause ] ]
  [ CHECK ( expr ) ]
  [ REFERENCES foreign_table ( col_name )
    [ ON DELETE { SET NULL | SET DEFAULT | CASCADE | RESTRICT | NO ACTION } ] ]

table_constraint:
[ CONSTRAINT name ]
{ PRIMARY KEY ( col_name [, …] ) |
  UNIQUE ( col_name [, …] ) |
  CHECK ( expr ) |
  FOREIGN KEY ( col_name [, …] )
    REFERENCES foreign_table ( col_name ) [ ON DELETE action ] }
""",

        "MySQL": """
Engine-specific rules for MySQL / MariaDB:
- Use: VARCHAR(n), CHAR(n), TEXT, MEDIUMTEXT, LONGTEXT, INT, BIGINT, SMALLINT, TINYINT,
  DECIMAL(p,s), FLOAT, DOUBLE, TINYINT(1) for BOOLEAN, DATE, DATETIME(6), TIMESTAMP(6), JSON.
- Auto-increment PK: col_name INT NOT NULL AUTO_INCREMENT PRIMARY KEY.
- Default storage engine: ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci.
- Supports ON DELETE CASCADE, ON UPDATE CASCADE.

Reference DDL syntax for MySQL:
CREATE [ TEMPORARY ] TABLE [ IF NOT EXISTS ] tbl_name (
  col_name data_type
    [ NOT NULL | NULL ]
    [ DEFAULT { literal | (expr) } ]
    [ AUTO_INCREMENT ]
    [ UNIQUE [KEY] ]
    [ PRIMARY KEY ]
    [ COMMENT 'string' ]
    [ REFERENCES ref_tbl (ref_col)
      [ ON DELETE reference_option ]
      [ ON UPDATE reference_option ] ]
  [, …]
  [, PRIMARY KEY ( col_name [, …] ) ]
  [, UNIQUE INDEX index_name ( col_name [, …] ) ]
  [, INDEX index_name ( col_name [, …] ) ]
  [, CONSTRAINT symbol FOREIGN KEY ( col_name [, …] )
       REFERENCES ref_tbl ( col_name [, …] )
       [ ON DELETE reference_option ]
       [ ON UPDATE reference_option ] ]
  [, CHECK ( expr ) [ [ NOT ] ENFORCED ] ]
)
[ ENGINE = InnoDB ]
[ DEFAULT CHARSET = charset_name ]
[ COLLATE = collation_name ]
[ COMMENT = 'string' ]
[ PARTITION BY … ]

reference_option: RESTRICT | CASCADE | SET NULL | NO ACTION | SET DEFAULT
""",

        "Redshift": """
Engine-specific rules for Amazon Redshift:
- Use: VARCHAR(n), CHAR(n), TEXT, INTEGER, BIGINT, SMALLINT,
  DECIMAL(p,s), REAL, DOUBLE PRECISION, BOOLEAN, DATE, TIMESTAMP, TIMESTAMPTZ, SUPER.
- Auto-increment: col_name INTEGER IDENTITY(0,1) NOT NULL.
- Foreign keys declared but NOT enforced.
- Do NOT add CREATE INDEX.
- Specify DISTKEY, SORTKEY.

Reference DDL syntax for Redshift:
CREATE [ [ LOCAL ] { TEMPORARY | TEMP } ] TABLE
[ IF NOT EXISTS ] table_name (
  column_name data_type
    [ DEFAULT default_expr ]
    [ IDENTITY ( seed, step ) ]
    [ ENCODE encoding ]
    [ NOT NULL | NULL ]
    [ UNIQUE ]
    [ PRIMARY KEY ]
    [ REFERENCES reftable ( refcolumn ) ]
  [, …]
  [, PRIMARY KEY ( column_name [, …] ) ]
  [, FOREIGN KEY ( column_name [, …] ) REFERENCES reftable ( column_name [, …] ) ]
  [, UNIQUE ( column_name [, …] ) ]
)
[ DISTSTYLE { AUTO | EVEN | KEY | ALL } ]
[ DISTKEY ( column_name ) ]
[ { COMPOUND | INTERLEAVED } SORTKEY ( column_name [, …] ) ]
[ ENCODE AUTO ]
[ BACKUP { YES | NO } ]
"""
    }

    return hints.get(db_type, f"\nUse standard SQL data types and constraints appropriate for {db_type}.\n")

# ————————————————————
# SCD Rules
# ————————————————————

_SCD_RULES = """
SCD (Slowly Changing Dimension) type selection rules — apply to EVERY dimension table:

- SCD Type 0 : Static / never changes.
- SCD Type 1 : Overwrite old value.
- SCD Type 2 : Add new row with effective/expiry dates and is_current flag.
- SCD Type 3 : Track only one previous value (add prev_<col> column).
- SCD Type 4 : Separate history table.
- SCD Type 6 : Hybrid of Type 1 + 2 + 3.

  For each dimension table, choose the most appropriate SCD type and document it in the table's "scd_type" field.
"""

# ————————————————————
# Prompt Summary
# ————————————————————

def get_prompt_summary(request: str, db_type: str, model_type: str) -> dict:

    engine_summary = {
        
  "BigQuery": "Uses INT64/STRING/BOOL types · Constraints exist but are not enforced · Fully managed serverless warehouse · No traditional indexes",
  "PostgreSQL": "Rich types like TEXT/JSONB/UUID · Supports GENERATED AS IDENTITY · Powerful indexing (including partial indexes) · Strong foreign key and CASCADE support",
  "MSSQL": "Uses NVARCHAR, DATETIME2, UNIQUEIDENTIFIER · IDENTITY(auto‑numbering) available · Robust transactional engine · Full CASCADE options",
  "Snowflake": "Uses VARCHAR/NUMBER/VARIANT · AUTOINCREMENT for surrogate keys · CLUSTER BY for performance tuning · No traditional indexes needed",
  "SQLite": "Lightweight embedded DB · TEXT/INTEGER/REAL types · Foreign keys only if PRAGMA enabled · Limited ALTER TABLE capabilities",
  "MySQL": "VARCHAR/INT/AUTO_INCREMENT · InnoDB with utf8mb4 support · Widely used transactional engine · Full CASCADE options for constraints",
  "Redshift": "VARCHAR/SUPER/IDENTITY types · Uses DISTKEY/SORTKEY for performance instead of indexes · Columnar warehouse optimized for analytics"

    }.get(db_type, f"Standard SQL for {db_type}")

    return {
        "db_engine": db_type,
        "model_type": model_type,
        "normal_form": "3NF" if model_type in ("relational", "both") else "N/A",
        "schema_pattern": "Star Schema" if model_type in ("analytical", "both") else "N/A",
        "engine_rules": engine_summary,
        "scd_applied": model_type in ("analytical", "both"),
        "scd_summary": "SCD 0–6 per dimension table" if model_type in ("analytical", "both") else "Not applicable",
        "namespace_extraction": "project.dataset auto-detected (BigQuery)" if db_type == "BigQuery" else "schema auto-detected from prompt",
    }

# ————————————————————
# Relational Model Prompt
# ————————————————————
def _relational_prompt(request: str, db_type: str, rag_context: str = "") -> str:
    rag_block = f"\n{rag_context}\n" if rag_context else ""

    return f"""
You are a senior database architect specialising in 3NF relational models.
{rag_block}

Target database: {db_type}

{_engine_hints(db_type)}

CRITICAL RULES:

1. Generate ONLY plain table names, NO dots, NO schema prefix, NO database prefix.
   CORRECT: "customers", "orders", "order_items"
   WRONG:   "mydb.customers", "dbo.orders", "sales.order_items"

2. Every column MUST have a "description" field.
3. Mark nullable columns explicitly.
4. Include all relevant indexes in a top-level "indexes" array.
5. Every table MUST have a "description" field.

6. COLUMN NAMING STANDARD:
   a. lowercase snake_case
   b. avoid generic terms (value, type, data)
   c. must express meaning & usage
   d. FK columns must end in "_id"
   e. Surrogate keys follow: <table_name>_sk

Output ONLY valid JSON:

{{
  "model_type": "relational",
  "normal_form": "3NF",
  "db_type": "{db_type}",
  "tables": [
    {{
      "name": "example_table",
      "description": "Stores …",
      "primary_key": ["id"],
      "columns": [
        {{
          "name": "id",
          "type": "…",
          "nullable": false,
          "primary_key": true,
          "description": "Auto-generated surrogate primary key"
        }},
        {{
          "name": "example_col",
          "type": "…",
          "nullable": false,
          "description": "Brief purpose of this column"
        }}
      ]
    }}
  ],
  "relationships": [
    {{
      "from_table": "child_table",
      "from_column": "fk_col",
      "to_table": "parent_table",
      "to_column": "id",
      "cardinality": "many-to-one"
    }}
  ],
  "indexes": []
}}

Use the RAG KNOWLEDGE BASE CONTEXT above (if provided) to enrich descriptions.

User Request: {request}
"""

# ————————————————————
# Analytical Model Prompt
# ————————————————————
def _analytical_prompt(request: str, db_type: str, rag_context: str = "") -> str:
    rag_block = f"\n{rag_context}\n" if rag_context else ""

    return f"""
You are a senior data warehouse architect specialising in STAR SCHEMA modelling.
{rag_block}

Target: {db_type}

{_engine_hints(db_type)}
{_SCD_RULES}

CRITICAL RULES:

1. Table names must be plain (no db/schema prefix).
2. Every table MUST have a "description".
3. Every column MUST have a "description".
4. Nullable must be explicitly marked.
5. Fact tables:
     - Measures → "is_measure": true
     - FKs → "is_foreign_key": true
6. Dimension tables:
     - Include "scd_type"
     - Include "scd_rationale"

7. COLUMN NAMING STANDARD:
   a. lowercase snake_case
   b. meaningful & unambiguous
   c. must reflect meaning and usage
   d. foreign keys end with "_id"
   e. surrogate keys use "<table_name>_sk"

8. If supported, include "partition_suggestions" with:
   - table
   - partition_by
   - cluster_by
   - rationale

Output ONLY valid JSON:

{{ 
  "model_type": "analytical",
  "schema_pattern": "star",
  "db_type": "{db_type}",

  "fact_tables": [
    {{
      "name": "fact_example",
      "description": "Central fact table storing …",
      "primary_key": ["fact_id"],
      "columns": [
        {{
          "name": "fact_id",
          "type": "…",
          "nullable": false,
          "primary_key": true,
          "description": "Surrogate primary key for this fact row"
        }},
        {{
          "name": "dim_id",
          "type": "…",
          "nullable": false,
          "is_foreign_key": true,
          "description": "Foreign key referencing dim_example"
        }},
        {{
          "name": "amount",
          "type": "…",
          "nullable": true,
          "is_measure": true,
          "description": "Transaction amount in base currency"
        }}
      ]
    }}
  ],

  "dimension_tables": [
    {{
      "name": "dim_example",
      "description": "Dimension storing …",
      "scd_type": 2,
      "scd_rationale": "Attributes change over time and must be historized",
      "primary_key": ["dim_id"],
      "columns": [
        {{
          "name": "dim_id",
          "type": "…",
          "nullable": false,
          "primary_key": true,
          "description": "Surrogate primary key"
        }}
      ]
    }}
  ],

  "relationships": [
    {{
      "from_table": "fact_example",
      "from_column": "dim_id",
      "to_table": "dim_example",
      "to_column": "dim_id",
      "cardinality": "many-to-one"
    }}
  ],

  "partition_suggestions": [
    {{
      "table": "fact_example",
      "partition_by": "order_date",
      "cluster_by": ["customer_id", "product_id"],
      "rationale": "Partition by date for time range queries; cluster by FKs for performance"
    }}
  ]
}}

User Request: {request}
"""

# ————————————————————
# Modification Prompt
# ————————————————————
def _modification_prompt(existing_model: dict, request: str) -> str:
    return f"""
You are a senior database architect.
Apply the requested modification to the existing model.

CRITICAL RULES:
1. Return the COMPLETE updated model as valid JSON — every table, every column, no omissions.
   Even if only one table changed, return ALL tables in full.
2. Keep plain table names (no schema prefix) — namespace is stamped separately.
3. Every column MUST retain or add a "description" field.
4. Every table MUST retain or add a "description" field.
5. Add a top-level "_changes" object with:
   - "summary": a single string of max 2 sentences describing what changed.
   - "added_tables": list of table name strings that are new.
   - "modified_tables": list of table name strings that had columns changed.
   - "added_columns": list of "table.column" strings for new columns.
   - "modified_columns": list of "table.column" strings for columns whose type or constraints changed.

Modification Request:
{request}

Existing Model:
{json.dumps(existing_model, indent=2)}
"""
# ————————————————————
# SchemaAgent Class
# ————————————————————

class SchemaAgent:

    def __init__(self, db_engine: str = "MySQL"):
        self.llm = _get_llm(temperature=0.1)
        self.db_type = db_engine or os.getenv("DATABASE_TYPE", "MySQL")

    def generate_relational_model(self, request: str) -> dict:

        if not self.llm:

            return {"error": "LLM not configured"}

        # Fetch RAG context — pass empty string if RAG not configured

        rag_context = ""

        if RAG_AVAILABLE:

            client = get_search_client()

            if client:

                # Build placeholder tables from request for initial RAG query

                # (no columns yet — use table-level concepts only)

                rag_context = build_rag_context_block(

                    [{"name": w, "columns": []} for w in request.split() if len(w) > 4],

                    client,

                )

        model = _invoke_llm(self.llm, _relational_prompt(request, self.db_type, rag_context))

        namespace = _extract_namespace(request, self.db_type)

        return _stamp_namespace(model, namespace, self.db_type)
 

    def generate_analytical_model(self, request: str) -> dict:
        if not self.llm:
            return {"error": "LLM not configured"}
        rag_context = ""
        if RAG_AVAILABLE:
            client = get_search_client()
            if client:
                rag_context = build_rag_context_block(
                    [{"name": w, "columns": []} for w in request.split() if len(w) > 4],
                    client,
                )
        model = _invoke_llm(self.llm, _analytical_prompt(request, self.db_type, rag_context))
        namespace = _extract_namespace(request, self.db_type)
        return _stamp_namespace(model, namespace, self.db_type)

    def apply_modification(self, existing_model: dict, request: str) -> dict:
        if not self.llm:
            return {"error": "LLM not configured"}
        result = _invoke_llm(self.llm, _modification_prompt(existing_model, request))
        # Extract _changes before returning so it's accessible at top level
        changes = result.pop("_changes", {})
        result["_changes"] = changes
        return result

    def process_create(self, request: str, model_type: str = "both") -> dict:
        result = {}

        if model_type in ("relational", "both"):
            result["relational_model"] = self.generate_relational_model(request)

        if model_type in ("analytical", "both"):
            result["analytical_model"] = self.generate_analytical_model(request)

        return result

    def process_modify(self, request: str, existing_model: dict) -> dict:

        result = {}

        all_changes = {}

        if "relational_model" in existing_model:

            modified = self.apply_modification(existing_model["relational_model"], request)

            all_changes = modified.pop("_changes", {})

            result["relational_model"] = modified

        if "analytical_model" in existing_model:

            modified = self.apply_modification(existing_model["analytical_model"], request)

            if not all_changes:

                all_changes = modified.pop("_changes", {})

            else:

                modified.pop("_changes", None)

            result["analytical_model"] = modified

        if not result:

            modified = self.apply_modification(existing_model, request)

            all_changes = modified.pop("_changes", {})

            if existing_model.get("model_type") == "analytical":

                result["analytical_model"] = modified

            else:

                result["relational_model"] = modified

        result["_changes"] = all_changes

        return result
 

# ————————————————————
# Convenience Functions
# ————————————————————

def create_schema(request: str, model_type: str = "both", db_engine: str = "MySQL") -> dict:
    return SchemaAgent(db_engine=db_engine).process_create(request, model_type=model_type)

def modify_schema(request: str, existing_model: dict, db_engine: str = "MySQL") -> dict:
    return SchemaAgent(db_engine=db_engine).process_modify(request, existing_model)