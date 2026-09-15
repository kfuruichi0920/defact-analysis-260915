"""Unit tests for QueryPlan validation and SQL compiler."""

import pytest
from defect_insight.build.column_catalog import ColumnCatalog, ColumnDefinition
from defect_insight.query.schema import QueryPlan, FilterCondition, LexicalSearchSpec
from defect_insight.query.validator import validate_query_plan
from defect_insight.query.compiler import compile_query_plan


@pytest.fixture
def test_catalog():
    return ColumnCatalog([
        ColumnDefinition("defect_id", "管理番号", "c_001", role="record_id"),
        ColumnDefinition("detect_phase", "検出工程", "c_002", role="ordered_category", capabilities={"filterable": True, "ordered": True}),
        ColumnDefinition("severity", "重要度", "c_003", role="category", capabilities={"filterable": True}),
        ColumnDefinition("title", "タイトル", "c_004", role="short_text", capabilities={"searchable": True, "filterable": True}),
        ColumnDefinition("cause", "原因", "c_005", role="long_text", capabilities={"searchable": True}),
    ])


def test_validate_query_plan_valid(test_catalog):
    plan = QueryPlan(
        analysis_mode="filtered_analysis",
        filters=[
            FilterCondition("detect_phase", "gte", 40),
            FilterCondition("severity", "eq", "高"),
        ],
        lexical_search=LexicalSearchSpec(required=True, columns=["title", "cause"], primary_terms=["タイマー"]),
    )
    res = validate_query_plan(plan, test_catalog)
    assert res.is_valid is True
    assert len(res.errors) == 0


def test_validate_query_plan_invalid_operator(test_catalog):
    plan = QueryPlan(
        analysis_mode="filtered_analysis",
        filters=[
            FilterCondition("severity", "gt", "高"),  # gt not allowed on standard category
        ],
    )
    res = validate_query_plan(plan, test_catalog)
    assert res.is_valid is False
    assert any("incompatible" in e for e in res.errors)


def test_compile_query_plan(test_catalog):
    plan = QueryPlan(
        analysis_mode="filtered_analysis",
        filters=[
            FilterCondition("detect_phase", "gte", 50),
            FilterCondition("severity", "eq", "高"),
        ],
        limit=100,
    )
    compiled = compile_query_plan(plan, test_catalog)
    assert 'WHERE "detect_phase_ordinal" >= ? AND "severity" = ? LIMIT 100' in compiled.sql_query
    assert compiled.sql_params == [50, "高"]
