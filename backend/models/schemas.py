from pydantic import BaseModel
from typing import Optional, Dict, Any, List
 
 
class UserInput(BaseModel):
    user_query: str
    context: Optional[str] = None
 
 
class SchemaOutput(BaseModel):
    action: str  # "CREATE" or "MODIFY"
    ddl_statements: List[str]  # Combined DDL statements
    schema_json: Dict[str, Any]  # Schema analysis/structure
    validation: Dict[str, Any]  # Validation results
    relational_ddl: Optional[List[str]] = None  # Relational model DDL (for CREATE)
    analytical_ddl: Optional[List[str]] = None  # Analytical model DDL (for CREATE)
    modification_ddl: Optional[List[str]] = None  # Modification statements (for MODIFY)
 