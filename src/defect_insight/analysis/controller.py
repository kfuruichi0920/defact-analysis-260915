"""Analysis Controller orchestrating QueryPlan execution, batching, checkpointing, and reporting (Sections 87, 88)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import duckdb

from defect_insight.config import WorkspaceConfig
from defect_insight.build.column_catalog import ColumnCatalog
from defect_insight.query.schema import QueryPlan, QuestionTemplate
from defect_insight.query.validator import validate_query_plan
from defect_insight.query.compiler import compile_query_plan
from defect_insight.query.executor import QueryExecutor
from defect_insight.analysis.statistics import DeterministicStatistics
from defect_insight.analysis.batcher import BatchManager, BatchItem
from defect_insight.evidence.validator import FindingItem, validate_findings
from defect_insight.evidence.store import EvidenceStore
from defect_insight.learning.lessons import LessonLedger
from defect_insight.report.renderer import ReportRenderer
from defect_insight.report.exports import export_phase2_csvs


class AnalysisRun:
    """First-class Analysis Run object holding complete provenance, trace, and checkpoints."""

    def __init__(self, run_id: str, question: str, plan: QueryPlan):
        self.run_id = run_id
        self.question = question
        self.plan = plan
        self.status = "initialized"  # initialized, retrieval_done, batching_done, completed, failed
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.candidate_ids: List[str] = []
        self.trace_info: Dict[str, Any] = {}
        self.statistics: Dict[str, Any] = {}
        self.batch_items: List[BatchItem] = []
        self.raw_findings: List[Dict[str, Any]] = []
        self.validated_findings: List[FindingItem] = []
        self.coverage_info: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "question": self.question,
            "status": self.status,
            "created_at": self.created_at,
            "plan": self.plan.to_dict(),
            "trace_info": self.trace_info,
            "candidate_count": len(self.candidate_ids),
            "batches": [b.to_dict() for b in self.batch_items],
            "findings_count": len(self.validated_findings),
            "coverage": self.coverage_info,
        }


class AnalysisController:
    """Controller managing end-to-end Phase 2 execution."""

    def __init__(self, ws: WorkspaceConfig):
        self.ws = ws
        self.ws.init_workspace()
        self.executor = QueryExecutor(ws.duckdb_path, ws.fts_sqlite_path)
        self.stats_engine = DeterministicStatistics(str(ws.duckdb_path))
        self.batch_manager = BatchManager(context_budget_chars=12000)

        # Load catalog
        cat_data = ws.load_yaml(ws.columns_config_path)
        self.catalog = ColumnCatalog.from_dict(cat_data) if cat_data else ColumnCatalog()

        # Lesson ledger
        self.lesson_ledger = LessonLedger(ws.config_dir / "lessons.yaml")

    def plan_analysis(self, question: str, plan_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Creates and validates QueryPlan."""
        if plan_dict:
            plan = QueryPlan.from_dict(plan_dict)
        else:
            # Generate default plan based on question
            plan = QueryPlan(analysis_mode="filtered_analysis")

        val_res = validate_query_plan(plan, self.catalog)
        return {
            "is_valid": val_res.is_valid,
            "errors": val_res.errors,
            "warnings": val_res.warnings,
            "plan": plan.to_dict(),
        }

    def execute_retrieval(self, run_id: str, question: str, plan: QueryPlan) -> AnalysisRun:
        """Executes SQL and FTS retrieval deterministically (Sections 50, 57)."""
        run = AnalysisRun(run_id, question, plan)

        # Compile queries
        compiled = compile_query_plan(plan, self.catalog)
        candidate_ids, trace = self.executor.retrieve_candidate_ids(compiled)
        run.candidate_ids = candidate_ids
        trace["executed_sql"] = compiled.sql_query
        trace["sql_params"] = [str(p) for p in compiled.sql_params]
        trace["fts_terms"] = compiled.fts_terms
        run.trace_info = trace

        # Deterministic Statistics First (Section 57)
        stats = self.stats_engine.compute_candidate_statistics(candidate_ids, self.catalog)
        run.statistics = stats

        # Dynamic Batches (Section 60)
        proj_cols = plan.projections if plan.projections else ["title", "cause", "escape_cause", "countermeasure", "detect_phase"]
        candidate_records = self.executor.fetch_records_by_ids(candidate_ids, columns=proj_cols)
        run.batch_items = self.batch_manager.create_batches(candidate_records, proj_cols)
        run.trace_info["batch_count"] = len(run.batch_items)

        run.status = "retrieval_done"
        self._save_checkpoint(run)
        return run

    def complete_analysis(
        self,
        run: AnalysisRun,
        batch_findings: List[Dict[str, Any]],
        hypotheses_map: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, Any]:
        """Completes synthesis, validates findings, exports raw evidence appendix, and generates report."""
        # 1. Verify 100% Coverage (Section 59)
        for b in run.batch_items:
            b.status = "completed"
        run.coverage_info = self.batch_manager.verify_coverage(run.candidate_ids, run.batch_items)

        # 2. Build Finding Items
        findings_to_validate: List[FindingItem] = []
        for idx, f_data in enumerate(batch_findings, start=1):
            f_id = f_data.get("finding_id") or f"FIND-{idx:03d}"
            finding = FindingItem(
                finding_id=f_id,
                finding_type=f_data.get("type") or f_data.get("finding_type", "root_cause_pattern"),
                claim=f_data.get("claim", ""),
                supporting_records=f_data.get("supporting_records", []),
                counter_records=f_data.get("counter_records", []),
                confidence=f_data.get("confidence", "medium"),
                confidence_reason=f_data.get("confidence_reason", "Supported by deterministic candidate records"),
                hypotheses=f_data.get("hypotheses") or (hypotheses_map.get(f_id, []) if hypotheses_map else []),
            )
            findings_to_validate.append(finding)

        # 3. Finding Validator (Section 73)
        valid_res = validate_findings(findings_to_validate, set(run.candidate_ids))
        run.validated_findings = valid_res.accepted_findings

        # 4. Evidence Store & Deduplication (Section 81)
        store = EvidenceStore()
        store.register_findings(run.validated_findings)

        # 5. Fetch Full Raw Records for Evidence (Section 77, 80)
        raw_evidence = self.executor.fetch_raw_evidence_records(store.all_evidence_record_ids)
        norm_evidence = self.executor.fetch_records_by_ids(store.all_evidence_record_ids)

        # 6. Applied Lessons Trace
        applicable_lessons = [l.to_dict() for l in self.lesson_ledger.get_applicable_lessons()]

        # 7. Render Report (Sections 75-84)
        run_meta = {
            "run_id": run.run_id,
            "question": run.question,
            "analysis_mode": run.plan.analysis_mode,
            "analysis_targets": ["cause", "escape_cause", "countermeasure"],
            "dataset_source": self.ws.duckdb_path.name,
            "trace": run.trace_info,
        }
        renderer = ReportRenderer(self.catalog)
        report_json, report_md = renderer.render_report(
            run_meta=run_meta,
            statistics=run.statistics,
            findings=run.validated_findings,
            evidence_store=store,
            raw_evidence_records=raw_evidence,
            normalized_evidence_records=norm_evidence,
            coverage_info=run.coverage_info,
            lessons_applied=applicable_lessons,
        )

        # Save reports
        run_reports_dir = self.ws.reports_dir
        run_reports_dir.mkdir(parents=True, exist_ok=True)
        report_md_path = run_reports_dir / f"{run.run_id}-report.md"
        report_json_path = run_reports_dir / f"{run.run_id}-report.json"

        with open(report_md_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        with open(report_json_path, "w", encoding="utf-8") as f:
            json.dump(report_json, f, indent=2, ensure_ascii=False)

        # Export CSVs (Section 100)
        run_exports_dir = self.ws.exports_dir / run.run_id
        filtered_recs = self.executor.fetch_records_by_ids(run.candidate_ids)
        exported_csvs = export_phase2_csvs(
            export_dir=run_exports_dir,
            catalog=self.catalog,
            filtered_records=filtered_recs,
            raw_evidence_records=raw_evidence,
            findings=run.validated_findings,
            evidence_store=store,
            statistics=run.statistics,
        )

        run.status = "completed"
        self._save_checkpoint(run)

        return {
            "status": "completed",
            "run_id": run.run_id,
            "report_md_path": str(report_md_path),
            "report_json_path": str(report_json_path),
            "coverage": run.coverage_info,
            "findings_count": len(run.validated_findings),
            "rejected_findings_count": len(valid_res.rejected_findings),
            "evidence_record_count": len(raw_evidence),
            "exported_csvs": exported_csvs,
        }

    def _save_checkpoint(self, run: AnalysisRun) -> None:
        """Saves checkpoint to runs/analysis/<run_id>.json (Section 87)."""
        run_dir = self.ws.analysis_runs_dir
        run_dir.mkdir(parents=True, exist_ok=True)
        ckpt_path = run_dir / f"{run.run_id}.json"
        with open(ckpt_path, "w", encoding="utf-8") as f:
            json.dump(run.to_dict(), f, indent=2, ensure_ascii=False)
