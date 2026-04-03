"""Formatter for schema generation workflow output"""
from backend.models.schemas import SchemaOutput
from typing import Dict, Any, List
 
 
def format_output(action: str,
                  schema_analysis: Dict[str, Any] = None,
                  relational_ddl: List[str] = None,
                  analytical_ddl: List[str] = None,
                  modification_ddl: List[str] = None,
                  validation: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Format schema generation output
    
    For CREATE action: includes both relational and analytical DDL
    For MODIFY action: includes modification DDL statements
    """
    if action == "CREATE":
        output = SchemaOutput(
            action=action,
            ddl_statements=(relational_ddl or []) + (analytical_ddl or []),
            schema_json=schema_analysis or {},
            validation=validation or {},
            relational_ddl=relational_ddl or [],
            analytical_ddl=analytical_ddl or []
        )
    elif action == "MODIFY":
        output = SchemaOutput(
            action=action,
            ddl_statements=modification_ddl or [],
            schema_json={},
            validation=validation or {},
            modification_ddl=modification_ddl or []
        )
    else:
        output = SchemaOutput(
            action=action,
            ddl_statements=[],
            schema_json={},
            validation=validation or {}
        )
    
    return output.model_dump()