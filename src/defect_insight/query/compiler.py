"""Deterministic QueryPlan to SQL and FTS query compiler (Sections 40, 41, 42)."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
from defect_insight.build.column_catalog import ColumnCatalog, ColumnDefinition
from defect_insight.query.schema import QueryPlan, FilterCondition


class CompiledQuery:
    """Represents safely compiled SQL and FTS queries."""

    def __init__(
        self,
        sql_query: str,
        sql_params: List[Any],
        fts_terms: List[str],
        fts_columns: List[str],
        fts_required: bool,
    ):
        self.sql_query = sql_query
        self.sql_params = sql_params
        self.fts_terms = fts_terms
        self.fts_columns = fts_columns
        self.fts_required = fts_required

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sql_query": self.sql_query,
            "sql_params": [str(p) for p in self.sql_params],
            "fts_terms": self.fts_terms,
            "fts_columns": self.fts_columns,
            "fts_required": self.fts_required,
        }


def escape_sql_identifier(identifier: str) -> str:
    """Safely escapes a SQL column/table identifier."""
    clean = identifier.replace('"', '""')
    return f'"{clean}"'


def compile_filter_condition(
    f: FilterCondition,
    catalog: ColumnCatalog,
) -> Tuple[str, List[Any]]:
    """Compiles a single FilterCondition into a safe SQL clause."""
    col = catalog.get_column(f.column_id)
    col_name = col.column_id if col else f.column_id
    escaped_col = escape_sql_identifier(col_name)

    # For ordered categories with ordinal comparison, compare against ordinal column if applicable
    if col and col.role == "ordered_category" and f.operator in ("lt", "lte", "gt", "gte", "between"):
        # If value is integer, compare against ordinal
        if isinstance(f.value, int) or (isinstance(f.value, str) and f.value.isdigit()):
            escaped_col = escape_sql_identifier(f"{col_name}_ordinal")
            val = int(f.value)
        else:
            val = f.value
    else:
        val = f.value

    op = f.operator
    if op == "eq":
        return f"{escaped_col} = ?", [val]
    elif op == "neq":
        return f"{escaped_col} != ?", [val]
    elif op == "in":
        placeholders = ", ".join(["?"] * len(val))
        return f"{escaped_col} IN ({placeholders})", list(val)
    elif op == "not_in":
        placeholders = ", ".join(["?"] * len(val))
        return f"{escaped_col} NOT IN ({placeholders})", list(val)
    elif op == "lt":
        return f"{escaped_col} < ?", [val]
    elif op == "lte":
        return f"{escaped_col} <= ?", [val]
    elif op == "gt":
        return f"{escaped_col} > ?", [val]
    elif op == "gte":
        return f"{escaped_col} >= ?", [val]
    elif op == "between":
        return f"{escaped_col} BETWEEN ? AND ?", [val[0], val[1]]
    elif op == "is_null":
        return f"({escaped_col} IS NULL OR {escaped_col} = '')", []
    elif op == "is_not_null":
        return f"({escaped_col} IS NOT NULL AND {escaped_col} != '')", []
    elif op == "contains":
        return f"{escaped_col} LIKE ?", [f"%{val}%"]
    elif op == "starts_with":
        return f"{escaped_col} LIKE ?", [f"{val}%"]
    elif op == "ends_with":
        return f"{escaped_col} LIKE ?", [f"%{val}"]
    else:
        raise ValueError(f"Unsupported filter operator '{op}'")


def compile_query_plan(plan: QueryPlan, catalog: ColumnCatalog) -> CompiledQuery:
    """Compiles QueryPlan into safe parameterized SQL and FTS specs."""
    where_clauses: List[str] = []
    params: List[Any] = []

    for f in plan.filters:
        clause, c_params = compile_filter_condition(f, catalog)
        where_clauses.append(clause)
        params.extend(c_params)

    # Base query against normalized_defects
    where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    limit_sql = f" LIMIT {plan.limit}" if plan.limit is not None else ""
    sql = f"SELECT record_id FROM normalized_defects{where_sql}{limit_sql}"

    # FTS specs
    fts_terms = plan.lexical_search.primary_terms + plan.lexical_search.expanded_terms
    fts_cols = plan.lexical_search.columns

    return CompiledQuery(
        sql_query=sql,
        sql_params=params,
        fts_terms=fts_terms,
        fts_columns=fts_cols,
        fts_required=plan.lexical_search.required and len(fts_terms) > 0,
    )
