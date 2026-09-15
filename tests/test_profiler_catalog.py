"""Unit tests for Column Catalog, Profiler, and Role inference."""

import pytest
from defect_insight.build.column_catalog import ColumnCatalog, ColumnDefinition, sanitize_column_id
from defect_insight.build.importer import RawRecord
from defect_insight.build.profiler import profile_records, build_catalog_from_profiles


def test_sanitize_column_id():
    assert sanitize_column_id("不具合番号") == "defect_id"
    assert sanitize_column_id("検出工程") == "detect_phase"
    assert sanitize_column_id("原因") == "cause"
    assert sanitize_column_id("123_custom") == "col_123_custom"


def test_profiler_and_role_inference():
    records = [
        RawRecord("R1", {"defect_id": "DEF-001", "detect_phase": "UT", "cause": "タイマー満了", "count": "10"}, "file.csv", 2),
        RawRecord("R2", {"defect_id": "DEF-002", "detect_phase": "結合試験", "cause": "排他制御不足", "count": "20"}, "file.csv", 3),
        RawRecord("R3", {"defect_id": "DEF-003", "detect_phase": "UT", "cause": "NULLポインタ", "count": "30"}, "file.csv", 4),
    ]
    columns = ["defect_id", "detect_phase", "cause", "count"]
    profiles = profile_records(records, columns)

    assert profiles["defect_id"].proposed_role == "record_id"
    assert profiles["detect_phase"].proposed_role == "ordered_category"
    assert profiles["cause"].proposed_role == "long_text"
    assert profiles["count"].proposed_role == "numeric"

    catalog = build_catalog_from_profiles(profiles)
    assert len(catalog.columns) == 4
    col_phase = catalog.get_column("detect_phase")
    assert col_phase is not None
    assert col_phase.role == "ordered_category"
    assert col_phase.capabilities["ordered"] is True
