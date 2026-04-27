"""
Physical model generation agent (relational and analytical).
"""
 
import json
import logging
from typing import Optional, Dict
from .schema_utils import get_llm, invoke_llm, extract_namespace, stamp_namespace, build_custom_kb_context, to_snake_case
from .scd_agent import apply_scd_to_dimension
 
logger = logging.getLogger(__name__)
 
# ————————————————————
# Name Conversion (Business → Snake Case)
# ————————————————————
 
def _convert_names_to_snake_case(model: dict) -> dict:
    """
    Convert physical model names from business-friendly to snake_case.
    Converts table/column names but preserves content/descriptions.
    """
    if not model or model.get("parse_error"):
        return model
   
    model = dict(model)
   
    # For relational models: convert table and column names
    if "tables" in model and model["tables"]:
        tables = []
        for table in model["tables"]:
            table = dict(table)
            table["name"] = to_snake_case(table["name"])
           
            if "columns" in table and table["columns"]:
                columns = []
                for col in table["columns"]:
                    col = dict(col)
                    col["name"] = to_snake_case(col["name"])
                    columns.append(col)
                table["columns"] = columns
           
            # Convert primary key references
            if "primary_key" in table:
                if isinstance(table["primary_key"], list):
                    table["primary_key"] = [to_snake_case(pk) for pk in table["primary_key"]]
                else:
                    table["primary_key"] = to_snake_case(table["primary_key"])
           
            tables.append(table)
        model["tables"] = tables
   
    # For analytical models: convert fact and dimension table names
    if "fact_tables" in model and model["fact_tables"]:
        tables = []
        for table in model["fact_tables"]:
            table = dict(table)
            table["name"] = to_snake_case(table["name"])
           
            if "columns" in table and table["columns"]:
                columns = []
                for col in table["columns"]:
                    col = dict(col)
                    col["name"] = to_snake_case(col["name"])
                    columns.append(col)
                table["columns"] = columns
            tables.append(table)
        model["fact_tables"] = tables
   
    if "dimension_tables" in model and model["dimension_tables"]:
        tables = []
        for table in model["dimension_tables"]:
            table = dict(table)
            table["name"] = to_snake_case(table["name"])
           
            if "columns" in table and table["columns"]:
                columns = []
                for col in table["columns"]:
                    col = dict(col)
                    col["name"] = to_snake_case(col["name"])
                    columns.append(col)
                table["columns"] = columns
            tables.append(table)
        model["dimension_tables"] = tables
   
    # Convert relationship references
    if "relationships" in model and model["relationships"]:
        rels = []
        for rel in model["relationships"]:
            rel = dict(rel)
           
            if "from_table" in rel:
                rel["from_table"] = to_snake_case(rel["from_table"])
            if "to_table" in rel:
                rel["to_table"] = to_snake_case(rel["to_table"])
            if "from_entity" in rel:
                rel["from_entity"] = to_snake_case(rel["from_entity"])
            if "to_entity" in rel:
                rel["to_entity"] = to_snake_case(rel["to_entity"])
           
            # Convert column references
            if "from_column" in rel:
                rel["from_column"] = to_snake_case(rel["from_column"])
            if "to_column" in rel:
                rel["to_column"] = to_snake_case(rel["to_column"])
           
            rels.append(rel)
        model["relationships"] = rels
   
    return model
 
# ————————————————————
# Engine-Specific Hints
# ————————————————————
 
def _engine_hints(db_type: str) -> str:
    """Get database-specific DDL hints and rules."""
    hints = {
         "BigQuery": """
Engine-specific rules for BigQuery:
-Table names MUST be fully qualified as 'project_id.dataset_id.table_name`. 
-Use the schema name as dataset_id and 'my_project' as a placeholder project_id. "
- "Example: `my_project.ecommerce.orders`"
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
 
    # Convert names to snake_case
    result = _convert_names_to_snake_case(result)
 
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
 
    # Convert names to snake_case
    result = _convert_names_to_snake_case(result)
 
    # Apply namespace
    result = stamp_namespace(result, namespace, db_type)
 
    return result
 
# ————————————————————
# Modification Prompt
# ————————————————————
 
def _modification_prompt(existing_model: dict, request: str) -> str:
    """Generate prompt for model modification."""
    # Extract existing table/dimension names to remind the LLM to preserve them
    existing_tables = []
    existing_dims = []
   
    if "tables" in existing_model:
        existing_tables = [t.get("name") for t in existing_model.get("tables", [])]
    if "fact_tables" in existing_model:
        existing_tables = [t.get("name") for t in existing_model.get("fact_tables", [])]
    if "dimension_tables" in existing_model:
        existing_dims = [t.get("name") for t in existing_model.get("dimension_tables", [])]
   
    preservation_notes = ""
    if existing_tables:
        preservation_notes += f"\nExisting tables: {', '.join(existing_tables)}"
    if existing_dims:
        preservation_notes += f"\nExisting dimension tables: {', '.join(existing_dims)}"
   
    return f"""
You are a senior database architect. Your task is to PRECISELY apply the requested changes and NOTHING MORE.
 
EXISTING MODEL:
{json.dumps(existing_model, indent=2)}
 
CHANGE REQUEST: {request}
 
CRITICAL INSTRUCTIONS - DO NOT DEVIATE:
1. Apply ONLY the EXACT changes specified in the change request
2. Do NOT infer or add any new attributes, columns, or tables not explicitly mentioned
3. Do NOT modify any existing columns, types, or properties unless the request specifically mentions them
4. Return the COMPLETE model with ALL existing content exactly preserved, with only the requested changes applied{preservation_notes}
5. If the request says "add column X", add ONLY column X - nothing else
6. If the request says "modify table Y", modify ONLY what's explicitly stated
7. Do NOT output explanations or comments - output the COMPLETE modified model as valid JSON only
 
EXAMPLES OF WRONG BEHAVIOR (DO NOT DO THIS):
- If request says "add reviews table", do NOT add new columns to other tables
- If request says "add email to customers", do NOT add other fields like phone or address
- If request says "rename table", do NOT change column types or add new columns
 
Output the COMPLETE modified model as valid JSON - no explanation, no comments.
"""
 
def modify_physical_model(existing_model: dict, request: str, db_type: str) -> dict:
    """Modify an existing physical model."""
    llm = get_llm()
    if not llm:
        return {"parse_error": True, "error": "LLM not available"}
 
    # Handle wrapped models (e.g., {"relational_model": {...}})
    model_to_modify = existing_model
    if "relational_model" in existing_model and "tables" not in existing_model:
        model_to_modify = existing_model["relational_model"]
    elif "analytical_model" in existing_model and "fact_tables" not in existing_model:
        model_to_modify = existing_model["analytical_model"]
 
    prompt = _modification_prompt(model_to_modify, request)
    result = invoke_llm(llm, prompt)
 
    if result.get("parse_error"):
        logger.error("Model modification failed")
        return result
 
    # Convert names to snake_case
    result = _convert_names_to_snake_case(result)
 
    return result
 