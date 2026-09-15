"""Question Template and QueryPlan Schema definitions (Sections 37-43)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
import yaml


class QuestionTemplate:
    """Structured question representation normalized from free-form user query (Section 37)."""

    def __init__(
        self,
        question: str,
        scope: Optional[Dict[str, Any]] = None,
        analysis_targets: Optional[List[str]] = None,
        analysis_mode: str = "auto",  # auto, case_investigation, filtered_analysis, landscape_analysis, data_quality_analysis
        depth: str = "standard",  # concise, standard, detailed
        prior_analysis_mode: str = "disabled",  # disabled, verified_only, reference, reuse
        output_preference: Optional[Dict[str, Any]] = None,
    ):
        self.question = question
        self.scope = scope or {}
        self.analysis_targets = analysis_targets or ["cause", "countermeasure"]
        self.analysis_mode = analysis_mode
        self.depth = depth
        self.prior_analysis_mode = prior_analysis_mode
        self.output_preference = output_preference or {"evidence_level": "detailed", "include_records": "representative"}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question,
            "scope": self.scope,
            "analysis_targets": self.analysis_targets,
            "analysis_mode": self.analysis_mode,
            "depth": self.depth,
            "prior_analysis": {"mode": self.prior_analysis_mode},
            "output": self.output_preference,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> QuestionTemplate:
        return cls(
            question=data.get("question", ""),
            scope=data.get("scope", {}),
            analysis_targets=data.get("analysis_targets", ["cause", "countermeasure"]),
            analysis_mode=data.get("analysis_mode", "auto"),
            depth=data.get("depth", "standard"),
            prior_analysis_mode=data.get("prior_analysis", {}).get("mode", "disabled"),
            output_preference=data.get("output", {}),
        )


class FilterCondition:
    """Single filtering condition in QueryPlan."""

    def __init__(
        self,
        column_id: str,
        operator: str,  # eq, neq, in, not_in, lt, lte, gt, gte, between, is_null, is_not_null, contains, starts_with, ends_with
        value: Any = None,
    ):
        self.column_id = column_id
        self.operator = operator.lower()
        self.value = value

    def to_dict(self) -> Dict[str, Any]:
        d = {"column_id": self.column_id, "operator": self.operator}
        if self.value is not None:
            d["value"] = self.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FilterCondition:
        return cls(
            column_id=data["column_id"],
            operator=data["operator"],
            value=data.get("value"),
        )


class LexicalSearchSpec:
    """FTS lexical search specification (Sections 39, 50, 51)."""

    def __init__(
        self,
        required: bool = False,
        columns: Optional[List[str]] = None,
        primary_terms: Optional[List[str]] = None,
        expanded_terms: Optional[List[str]] = None,
    ):
        self.required = required
        self.columns = columns or ["title", "cause"]
        self.primary_terms = primary_terms or []
        self.expanded_terms = expanded_terms or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "required": self.required,
            "columns": self.columns,
            "primary_terms": self.primary_terms,
            "expanded_terms": self.expanded_terms,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LexicalSearchSpec:
        return cls(
            required=data.get("required", False),
            columns=data.get("columns", ["title", "cause"]),
            primary_terms=data.get("primary_terms", []),
            expanded_terms=data.get("expanded_terms", []),
        )


class SemanticFilterSpec:
    """Specification for meaning-based filtering by AI Agent (Sections 53, 54)."""

    def __init__(self, required: bool = False, condition: str = "", target_columns: Optional[List[str]] = None):
        self.required = required
        self.condition = condition
        self.target_columns = target_columns or ["cause", "injection_cause"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "required": self.required,
            "condition": self.condition,
            "target_columns": self.target_columns,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SemanticFilterSpec:
        return cls(
            required=data.get("required", False),
            condition=data.get("condition", ""),
            target_columns=data.get("target_columns", ["cause", "injection_cause"]),
        )


class QueryPlan:
    """Structured Analysis Plan validated and executed by Python Engine (Section 39)."""

    def __init__(
        self,
        analysis_mode: str,
        filters: Optional[List[FilterCondition]] = None,
        lexical_search: Optional[LexicalSearchSpec] = None,
        semantic_filter: Optional[SemanticFilterSpec] = None,
        projections: Optional[List[str]] = None,
        group_by: Optional[List[str]] = None,
        limit: Optional[int] = None,
        planner_notes: Optional[str] = None,
    ):
        self.analysis_mode = analysis_mode
        self.filters = filters or []
        self.lexical_search = lexical_search or LexicalSearchSpec()
        self.semantic_filter = semantic_filter or SemanticFilterSpec()
        self.projections = projections or []
        self.group_by = group_by or []
        self.limit = limit
        self.planner_notes = planner_notes or ""

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "analysis_mode": self.analysis_mode,
            "filters": [f.to_dict() for f in self.filters],
            "lexical_search": self.lexical_search.to_dict(),
            "semantic_filter": self.semantic_filter.to_dict(),
            "projections": self.projections,
            "group_by": self.group_by,
        }
        if self.limit is not None:
            d["limit"] = self.limit
        if self.planner_notes:
            d["planner_notes"] = self.planner_notes
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> QueryPlan:
        filters = [FilterCondition.from_dict(f) for f in data.get("filters", [])]
        lexical = LexicalSearchSpec.from_dict(data.get("lexical_search", {}))
        semantic = SemanticFilterSpec.from_dict(data.get("semantic_filter", {}))
        return cls(
            analysis_mode=data.get("analysis_mode", "filtered_analysis"),
            filters=filters,
            lexical_search=lexical,
            semantic_filter=semantic,
            projections=data.get("projections", []),
            group_by=data.get("group_by", []),
            limit=data.get("limit"),
            planner_notes=data.get("planner_notes"),
        )
