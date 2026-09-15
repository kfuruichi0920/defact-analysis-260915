"""QueryPlan validation against Column Catalog and allowed operators (Sections 40, 41)."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
from defect_insight.build.column_catalog import ColumnCatalog, ColumnDefinition
from defect_insight.query.schema import QueryPlan, FilterCondition

ALLOWED_OPERATORS = {
    "eq",
    "neq",
    "in",
    "not_in",
    "lt",
    "lte",
    "gt",
    "gte",
    "between",
    "is_null",
    "is_not_null",
    "contains",
    "starts_with",
    "ends_with",
}

ROLE_OPERATOR_COMPATIBILITY = {
    "category": {"eq", "neq", "in", "not_in", "is_null", "is_not_null"},
    "status": {"eq", "neq", "in", "not_in", "is_null", "is_not_null"},
    "ordered_category": {"eq", "neq", "in", "not_in", "lt", "lte", "gt", "gte", "between", "is_null", "is_not_null"},
    "date": {"eq", "neq", "lt", "lte", "gt", "gte", "between", "is_null", "is_not_null"},
    "numeric": {"eq", "neq", "lt", "lte", "gt", "gte", "between", "is_null", "is_not_null"},
    "record_id": {"eq", "neq", "in", "not_in", "is_null", "is_not_null", "starts_with"},
    "short_text": {"eq", "neq", "contains", "starts_with", "ends_with", "is_null", "is_not_null"},
    "long_text": {"contains", "is_null", "is_not_null"},
    "ignore": set(),
}


class QueryPlanValidationResult:
    """Validation report for QueryPlan."""

    def __init__(self, is_valid: bool = True, errors: Optional[List[str]] = None, warnings: Optional[List[str]] = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def validate_query_plan(plan: QueryPlan, catalog: ColumnCatalog) -> QueryPlanValidationResult:
    """Strictly validates QueryPlan against ColumnCatalog (Section 40)."""
    errors: List[str] = []
    warnings: List[str] = []

    # 1. Validate analysis mode
    valid_modes = {"case_investigation", "filtered_analysis", "landscape_analysis", "data_quality_analysis"}
    if plan.analysis_mode not in valid_modes:
        errors.append(f"Invalid analysis_mode '{plan.analysis_mode}'. Must be one of {sorted(valid_modes)}.")

    # 2. Validate filters
    for idx, f in enumerate(plan.filters):
        col = catalog.get_column(f.column_id)
        if not col:
            errors.append(f"Filter #{idx + 1}: Unknown column '{f.column_id}' does not exist in Column Catalog.")
            continue

        if not col.capabilities.get("filterable", False):
            errors.append(f"Filter #{idx + 1}: Column '{col.column_id}' is not marked as filterable in Catalog.")

        if f.operator not in ALLOWED_OPERATORS:
            errors.append(f"Filter #{idx + 1}: Operator '{f.operator}' is not in allowed operators list.")
            continue

        allowed_for_role = ROLE_OPERATOR_COMPATIBILITY.get(col.role, set())
        if f.operator not in allowed_for_role:
            errors.append(
                f"Filter #{idx + 1}: Operator '{f.operator}' is incompatible with column '{col.column_id}' role '{col.role}'."
            )

        # Check operator values
        if f.operator in ("in", "not_in"):
            if not isinstance(f.value, list) or len(f.value) == 0:
                errors.append(f"Filter #{idx + 1}: Operator '{f.operator}' requires a non-empty list of values.")
        elif f.operator == "between":
            if not isinstance(f.value, (list, tuple)) or len(f.value) != 2:
                errors.append(f"Filter #{idx + 1}: Operator 'between' requires a 2-element range [min, max].")
        elif f.operator in ("is_null", "is_not_null"):
            pass
        else:
            if f.value is None or (isinstance(f.value, str) and not f.value.strip()):
                errors.append(f"Filter #{idx + 1}: Operator '{f.operator}' requires a non-empty value.")

    # 3. Validate lexical search
    if plan.lexical_search.required:
        for col_id in plan.lexical_search.columns:
            col = catalog.get_column(col_id)
            if not col:
                warnings.append(f"Lexical search column '{col_id}' not found in catalog; ignoring.")
            elif not col.capabilities.get("searchable", False):
                warnings.append(f"Lexical search column '{col_id}' is not marked as searchable.")

        all_terms = plan.lexical_search.primary_terms + plan.lexical_search.expanded_terms
        if not all_terms:
            errors.append("Lexical search is marked as required, but neither primary_terms nor expanded_terms are provided.")

    # 4. Validate semantic filter
    if plan.semantic_filter.required:
        if not plan.semantic_filter.condition or not plan.semantic_filter.condition.strip():
            errors.append("Semantic filter is marked as required, but no condition description is specified.")

    return QueryPlanValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
