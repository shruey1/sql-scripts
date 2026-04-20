"""
SCD (Slowly Changing Dimension) detection and application agent.
"""

import logging

logger = logging.getLogger(__name__)

def detect_scd_type_for_column(col_name: str, col_description: str = "", table_description: str = "") -> dict:
    """
    Automatically detect and assign SCD type for a dimension column.
    Returns {"scd_type": int, "reason": str}
    """
    col_lower = col_name.lower()
    desc_lower = (col_description + " " + table_description).lower()

    # SCD Type 0: Static columns (rarely change)
    static_keywords = ["code", "id", "identifier", "static", "immutable", "guid", "sku"]
    if any(kw in col_lower for kw in static_keywords) or any(kw in desc_lower for kw in static_keywords):
        return {
            "scd_type": 0,
            "reason": "Static/immutable identifier that never changes"
        }

    # SCD Type 2: Historical tracking (created_at, updated_at, effective_date, expiry_date, is_current)
    scd2_keywords = [
        "created", "created_at", "created_date",
        "updated", "updated_at", "updated_date",
        "effective", "expiry", "expiration",
        "is_current", "iscurrent", "current_flag",
        "version", "start_date", "end_date",
        "audit", "timestamp"
    ]
    if any(kw in col_lower for kw in scd2_keywords) or any(kw in desc_lower for kw in scd2_keywords):
        return {
            "scd_type": 2,
            "reason": "Temporal/audit column tracking changes over time"
        }

    # SCD Type 3: Previous value tracking (prev_*, old_*)
    scd3_keywords = ["prev", "previous", "old", "last", "prior"]
    if any(kw in col_lower for kw in scd3_keywords):
        return {
            "scd_type": 3,
            "reason": "Tracks only the previous value of a slowly changing attribute"
        }

    # Default to SCD Type 1: Overwrite (most descriptive attributes)
    return {
        "scd_type": 1,
        "reason": "Descriptive attribute; changes overwrite old value"
    }

def apply_scd_to_dimension(dimension_table: dict) -> dict:
    """
    Apply SCD detection to all columns in a dimension table.
    Updates the table dict with scd_type and scd_rationale fields.
    Adds necessary SCD columns based on the detected SCD type.
    """
    if not isinstance(dimension_table, dict):
        return dimension_table

    table_name = dimension_table.get("name", "")
    table_desc = dimension_table.get("description", "")
    columns = dimension_table.get("columns", [])

    # Determine overall SCD type for the table
    scd_types_used = {}
    column_scd_details = []

    for col in columns:
        col_name = col.get("name", "")
        col_desc = col.get("description", "")

        scd_info = detect_scd_type_for_column(col_name, col_desc, table_desc)
        scd_type = scd_info["scd_type"]

        scd_types_used[scd_type] = scd_types_used.get(scd_type, 0) + 1
        column_scd_details.append({
            "column": col_name,
            "scd_type": scd_type,
            "reason": scd_info["reason"]
        })

    # Determine overall table SCD strategy
    if 2 in scd_types_used:
        overall_scd = 2
        rationale = "Contains temporal/audit columns (SCD 2) — track full history with effective/expiry dates and current flag"
    elif 3 in scd_types_used:
        overall_scd = 3
        rationale = "Tracks previous values of changing attributes (SCD 3) — add prev_<column> for one prior value"
    else:
        most_common_scd = max(scd_types_used.keys()) if scd_types_used else 1
        rationale_map = {
            0: "Static dimension — values do not change",
            1: "Changes overwrite old values (SCD 1) — simple and straightforward",
        }
        overall_scd = most_common_scd
        rationale = rationale_map.get(most_common_scd, f"SCD Type {most_common_scd} applied")

    result = dict(dimension_table)
    result["scd_type"] = overall_scd
    result["scd_rationale"] = rationale
    result["_scd_column_details"] = column_scd_details

    # Add SCD-specific columns based on the detected type
    new_columns = list(columns)  # Copy existing columns

    if overall_scd == 2:
        # SCD Type 2: Add temporal tracking columns
        scd2_columns = [
            {
                "name": "effective_date",
                "type": "TIMESTAMP",
                "nullable": False,
                "description": "Date when this record became effective (SCD 2)",
                "default": "CURRENT_TIMESTAMP"
            },
            {
                "name": "expiry_date",
                "type": "TIMESTAMP",
                "nullable": True,
                "description": "Date when this record expired (SCD 2), NULL for current record"
            },
            {
                "name": "is_current",
                "type": "BOOLEAN",
                "nullable": False,
                "description": "Flag indicating if this is the current active record (SCD 2)",
                "default": "TRUE"
            }
        ]
        new_columns.extend(scd2_columns)

    elif overall_scd == 3:
        # SCD Type 3: Add previous value columns for changing attributes
        changing_columns = []
        for col in columns:
            col_name = col.get("name", "").lower()
            if not any(static in col_name for static in ["id", "code", "key", "sk", "created", "updated", "effective", "expiry", "is_current"]):
                changing_columns.append(col)

        # Add prev_ columns for up to 3 most likely changing attributes
        for col in changing_columns[:3]:
            col_name = col.get("name", "")
            prev_col = {
                "name": f"prev_{col_name}",
                "type": col.get("type", "VARCHAR(255)"),
                "nullable": True,
                "description": f"Previous value of {col_name} (SCD 3)"
            }
            new_columns.append(prev_col)

    # Update the columns in the result
    result["columns"] = new_columns

    logger.info("Applied SCD to dimension '%s': type=%d, rationale=%s, added %d columns",
                table_name, overall_scd, rationale, len(new_columns) - len(columns))

    return result