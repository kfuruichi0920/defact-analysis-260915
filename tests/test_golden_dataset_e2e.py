"""Comprehensive Golden Dataset End-to-End Test (Section 105)."""

import json
from pathlib import Path
import duckdb
import pytest

from defect_insight.config import WorkspaceConfig
from defect_insight.build.builder import BuildPipeline
from defect_insight.analysis.controller import AnalysisController
from defect_insight.query.schema import QueryPlan, FilterCondition, LexicalSearchSpec
from defect_insight.learning.lessons import LessonLedger, Lesson


def test_golden_dataset_full_pipeline_e2e(tmp_path: Path):
    ws = WorkspaceConfig(tmp_path)
    ws.init_workspace()

    csv_source = Path(__file__).parent / "data" / "golden_defects.csv"
    assert csv_source.exists(), "Golden defects CSV must exist"

    pipeline = BuildPipeline(ws)

    # 1. Phase 1: Propose
    prop_res = pipeline.propose(csv_source, id_column="管理番号")
    assert prop_res["status"] == "proposed"
    assert prop_res["total_records"] == 50

    # 2. Phase 1: Finalize Build
    build_res = pipeline.finalize_build(csv_source, id_column="管理番号", auto_accept_all_pending=True)
    assert build_res["status"] == "completed"
    assert build_res["total_records"] == 50
    assert ws.duckdb_path.exists()
    assert ws.fts_sqlite_path.exists()

    # Verify 1: UT -> 単体試験 normalization (Section 105)
    con = duckdb.connect(str(ws.duckdb_path), read_only=True)
    ut_rows = con.execute("SELECT detect_phase, detect_phase_label, detect_phase_ordinal FROM normalized_defects WHERE record_id = 'DEF-0002';").fetchall()
    assert ut_rows[0][0] == "phase_unit_test"
    assert ut_rows[0][1] == "単体試験"
    assert ut_rows[0][2] == 40

    # Verify 2: Raw narrative cause text is NOT altered (Section 105, 18)
    cause_rows = con.execute("SELECT cause, cause_raw FROM normalized_defects n JOIN raw_defects r ON n.record_id = r.record_id WHERE n.record_id = 'DEF-0001';").fetchall()
    norm_cause, raw_cause = cause_rows[0]
    assert "通信制御スレッドにおいてタイマー満了イベント" in norm_cause
    assert norm_cause == raw_cause

    # Verify 3: Semantic filter annotations are NOT written to prepared database (Section 54, 109)
    col_names = [desc[0] for desc in con.execute("DESCRIBE normalized_defects;").fetchall()]
    assert not any("semantic_annotation" in c for c in col_names)
    assert not any("llm_reasoning" in c for c in col_names)
    con.close()

    # 3. Phase 2: Analysis Execution
    controller = AnalysisController(ws)

    # Query: Filtered analysis on integration test and above (ordinal >= 50) AND FTS search for "タイマー"
    plan = QueryPlan(
        analysis_mode="filtered_analysis",
        filters=[
            FilterCondition("detect_phase", "gte", 50),
        ],
        lexical_search=LexicalSearchSpec(
            required=True,
            columns=["title", "cause"],
            primary_terms=["タイマー"],
            expanded_terms=["ウォッチドッグ"],
        ),
        projections=["defect_id", "title", "cause", "escape_cause", "countermeasure", "detect_phase"],
    )

    run = controller.execute_retrieval(
        run_id="RUN-GOLDEN-01",
        question="結合試験以降で発生したタイマー関連不具合の根本原因と流出要因を分析したい",
        plan=plan,
    )

    # Verify 4: SQL + FTS retrieval candidates count
    assert run.candidate_ids
    assert "DEF-0001" in run.candidate_ids  # Matches both phase (結合試験) and FTS (タイマー)
    assert "DEF-0011" in run.candidate_ids  # Matches ウォッチドッグタイマ
    assert "DEF-0002" not in run.candidate_ids  # Excluded by phase (UT)

    # Verify 5: Deterministic statistics computed first (Section 57)
    assert run.statistics["total_candidates"] == len(run.candidate_ids)
    assert "distributions" in run.statistics
    assert "detect_phase" in run.statistics["distributions"]

    # 4. Synthesize Batch Findings with Counter Evidence (Section 71)
    supp_records = [rid for rid in ["DEF-0001", "DEF-0004", "DEF-0008", "DEF-0024"] if rid in run.candidate_ids]
    counter_records = [rid for rid in ["DEF-0011"] if rid in run.candidate_ids]

    findings = [
        {
            "finding_id": "FIND-001",
            "type": "root_cause_pattern",
            "claim": "非同期処理におけるタイマー満了イベントと再送処理の排他制御不備",
            "supporting_records": supp_records,
            "counter_records": counter_records,
            "confidence": "high",
            "confidence_reason": "結合試験以降で多発しており全数集計で一致",
            "hypotheses": [
                "タイマーキャンセルとイベント受信の競合を防ぐ共通同期ユーティリティを設計標準化すべき"
            ],
        }
    ]

    comp_res = controller.complete_analysis(run, findings)
    assert comp_res["status"] == "completed"

    # Verify 6: 100% Coverage guaranteed in filtered_analysis (Section 59)
    assert comp_res["coverage"]["is_100_percent_covered"] is True
    assert comp_res["coverage"]["coverage_percentage"] == 100.0

    # Verify 7: Report Markdown and Raw Evidence Appendix (Sections 75-84)
    report_md_path = Path(comp_res["report_md_path"])
    assert report_md_path.exists()
    report_content = report_md_path.read_text(encoding="utf-8")

    # Executive summary, findings, counter evidence, evidence appendix exist
    assert "## 2. Executive Summary" in report_content
    assert "## 7. Findings & Insights" in report_content
    assert "## 9. Counter Evidence & Analysis Limitations" in report_content
    assert "## 12. Evidence Raw Data Appendix" in report_content
    assert "DEF-0001" in report_content
    assert "DEF-0011" in report_content

    # Verify 8: Checkpoint file exists (Section 87)
    ckpt_file = ws.analysis_runs_dir / "RUN-GOLDEN-01.json"
    assert ckpt_file.exists()

    # Verify 9: Candidate Lesson cannot exclude records (Section 95)
    ledger = LessonLedger(ws.config_dir / "lessons.yaml")
    lesson = Lesson(
        lesson_id="LES-001",
        feedback_id="FB-001",
        run_id="RUN-GOLDEN-01",
        lesson_type="retrieval_feedback",
        user_feedback="タイマー不具合ではウォッチドッグも含める",
        derived_lesson="ウォッチドッグを検索拡張語に含める",
        status="candidate",  # Candidate status
    )
    ledger.add_lesson(lesson)

    # Re-retrieve with Candidate lesson check
    applicable = ledger.get_applicable_lessons(only_accepted=True)
    assert len(applicable) == 0  # Candidate not returned for strict accepted rule
    applicable_all = ledger.get_applicable_lessons(only_accepted=False)
    assert len(applicable_all) == 1

    # Verify 10: License report and SBOM exist
    assert (ws.root / "license-report.md").exists()
    assert (ws.root / "sbom.spdx.json").exists()
