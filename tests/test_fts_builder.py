"""Unit tests for SQLite FTS5 trigram lexical search."""

import pytest
from pathlib import Path
from defect_insight.build.column_catalog import ColumnCatalog, ColumnDefinition
from defect_insight.build.importer import RawRecord
from defect_insight.build.fts_builder import FTSIndexBuilder


def test_fts5_trigram_search(tmp_path: Path):
    db_path = tmp_path / "test_fts.sqlite"
    builder = FTSIndexBuilder(db_path)

    catalog = ColumnCatalog([
        ColumnDefinition("defect_id", "管理番号", "c_001", role="record_id"),
        ColumnDefinition("title", "タイトル", "c_002", role="short_text", capabilities={"searchable": True}),
        ColumnDefinition("cause", "原因", "c_003", role="long_text", capabilities={"searchable": True}),
    ])

    records = [
        RawRecord("REC-01", {"管理番号": "DEF-01", "タイトル": "タイムアウトエラー", "原因": "排他制御ロック不足"}, "f.csv", 2),
        RawRecord("REC-02", {"管理番号": "DEF-02", "タイトル": "画面クラッシュ", "原因": "NULLポインタ参照"}, "f.csv", 3),
        RawRecord("REC-03", {"管理番号": "DEF-03", "タイトル": "バッチ通信遅延", "原因": "タイマー満了と競合"}, "f.csv", 4),
    ]

    info = builder.build_index(records, catalog)
    assert info["status"] == "success"
    assert info["total_indexed_records"] == 3

    # Search by Japanese term
    res_timer = builder.search(["タイマー"])
    assert res_timer == ["REC-03"]

    # Search in specific column
    res_title = builder.search(["タイムアウト"], columns=["title"])
    assert res_title == ["REC-01"]
