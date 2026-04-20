"""
Agent responsible for generating structured JSON data models.
Main SchemaAgent class and convenience functions.
"""

import os
import logging
from typing import Optional, Dict

# Import from split modules
from .schema_utils import get_llm, invoke_llm, extract_namespace, stamp_namespace, build_custom_kb_context
from .logical_agent import create_logical_model
from .physical_agent import create_relational_model, create_analytical_model, modify_physical_model
from .scd_agent import apply_scd_to_dimension

logger = logging.getLogger(__name__)

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
        "normal_form": "3NF" if model_type == "relational" else "N/A",
        "schema_pattern": "Star Schema" if model_type == "analytical" else "N/A",
        "engine_rules": engine_summary,
        "scd_applied": model_type == "analytical",
        "scd_summary": "SCD 0–6 per dimension table" if model_type == "analytical" else "Not applicable",
        "namespace_extraction": "project.dataset auto-detected (BigQuery)" if db_type == "BigQuery" else "schema auto-detected from prompt",
    }

# ————————————————————
# SchemaAgent Class
# ————————————————————

class SchemaAgent:
    def __init__(self, db_engine: str = "MySQL"):
        self.llm = get_llm(temperature=0.1)
        self.db_type = db_engine or os.getenv("DATABASE_TYPE", "MySQL")

    def _validate_physical_model(self, physical_model: dict, logical_model: dict, model_type: str) -> dict:
        """
        Validate that physical model preserves all entities from logical model.
        Returns validated model or error dict.
        """
        if not logical_model or logical_model.get("error") or not physical_model or physical_model.get("error"):
            return physical_model

        logical_entities = logical_model.get("entities", [])
        logical_count = len(logical_entities)

        if model_type == "relational":
            physical_tables = physical_model.get("tables", [])
            physical_count = len(physical_tables)

            if physical_count != logical_count:
                logger.error(
                    f"❌ RELATIONAL MODEL VIOLATION: Expected {logical_count} tables, got {physical_count}. "
                    f"Logical entities: {[e.get('name') for e in logical_entities]}. "
                    f"Physical tables: {[t.get('name') for t in physical_tables]}"
                )
                return {
                    "error": f"Physical model must have exactly {logical_count} tables (one per logical entity). "
                           f"Found {physical_count} tables instead. New attributes are allowed, but not new tables.",
                    "logical_entities": logical_count,
                    "physical_tables": physical_count,
                    "expected_entities": [e.get("name") for e in logical_entities],
                    "actual_tables": [t.get("name") for t in physical_tables]
                }

        elif model_type == "analytical":
            dimension_tables = physical_model.get("dimension_tables", [])
            physical_count = len(dimension_tables)

            if physical_count != logical_count:
                logger.error(
                    f"❌ ANALYTICAL MODEL VIOLATION: Expected {logical_count} dimension tables, got {physical_count}. "
                    f"Logical entities: {[e.get('name') for e in logical_entities]}. "
                    f"Physical dimensions: {[t.get('name') for t in dimension_tables]}"
                )
                return {
                    "error": f"Physical model must have exactly {logical_count} dimension tables (one per logical entity). "
                           f"Found {physical_count} dimension tables instead. New attributes are allowed, but not new tables.",
                    "logical_entities": logical_count,
                    "physical_dimensions": physical_count,
                    "expected_entities": [e.get("name") for e in logical_entities],
                    "actual_dimensions": [t.get("name") for t in dimension_tables]
                }

        logger.info(f"✅ {model_type.upper()} MODEL VALIDATION PASSED: {physical_count} tables match {logical_count} entities")
        return physical_model

    def generate_logical_model(self, request: str, custom_kb: dict | None = None, model_type: str = "relational") -> dict:
        """Generate logical model using the logical_agent module."""
        return create_logical_model(request, self.db_type, model_type, custom_kb)

    def generate_relational_model(
        self,
        request: str,
        logical_model: dict | None = None,
        custom_kb: dict | None = None
    ) -> dict:
        """Generate relational model using the physical_agent module."""
        return create_relational_model(request, self.db_type, logical_model, custom_kb)

    def generate_analytical_model(
        self,
        request: str,
        logical_model: dict | None = None,
        custom_kb: dict | None = None
    ) -> dict:
        """Generate analytical model using the physical_agent module."""
        return create_analytical_model(request, self.db_type, logical_model, custom_kb)

    def apply_modification(self, existing_model: dict, request: str) -> dict:
        """Apply modifications using the physical_agent module."""
        return modify_physical_model(existing_model, request, self.db_type)

    def process_create(
        self,
        request: str,
        model_type: str = "relational",
        logical_model: dict | None = None,
        custom_kb: dict | None = None
    ) -> dict:
        """Process create request."""
        result = {}

        if model_type == "relational":
            result["relational_model"] = self.generate_relational_model(
                request,
                logical_model,
                custom_kb,
            )
        elif model_type == "analytical":
            result["analytical_model"] = self.generate_analytical_model(
                request,
                logical_model,
                custom_kb,
            )

        return result

    def process_modify(self, request: str, existing_model: dict) -> dict:
        """Process modify request."""
        result = {}
        all_changes = {}

        if "relational_model" in existing_model:
            modified = self.apply_modification(
                existing_model["relational_model"], request
            )
            all_changes = modified.pop("_changes", {})
            result["relational_model"] = modified

        if "analytical_model" in existing_model:
            modified = self.apply_modification(
                existing_model["analytical_model"], request
            )

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

def create_schema(
    request: str,
    model_type: str = "relational",
    db_engine: str = "MySQL",
    logical_model: Optional[Dict] = None,
    custom_kb: Optional[Dict] = None
) -> Dict:
    """Convenience function to create a schema."""
    return SchemaAgent(db_engine=db_engine).process_create(
        request,
        model_type=model_type,
        logical_model=logical_model,
        custom_kb=custom_kb
    )

def modify_schema(request: str, existing_model: dict, db_engine: str = "MySQL") -> dict:
    """Convenience function to modify a schema."""
    return SchemaAgent(db_engine=db_engine).process_modify(request, existing_model)