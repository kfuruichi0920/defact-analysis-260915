"""Command-line interface for defect-insight (Section 101)."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any

from defect_insight.config import WorkspaceConfig
from defect_insight.build.builder import BuildPipeline
from defect_insight.analysis.controller import AnalysisController
from defect_insight.analysis.quality import DataQualityAuditor, LandscapeAnalyzer
from defect_insight.query.schema import QueryPlan
from defect_insight.learning.feedback import FeedbackRecorder
from defect_insight.learning.lessons import LessonLedger
from defect_insight.provenance.license import generate_license_report, generate_spdx_sbom


def print_output(data: Any, as_json: bool = False) -> None:
    """Helper to output formatted JSON or human readable text."""
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        if isinstance(data, dict):
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(data)


def main() -> None:
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--workspace", "-w", type=str, default=None, help="Path to workspace root")
    common_parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    parser = argparse.ArgumentParser(
        prog="defect-insight",
        description="Deterministic AI-assisted defect table analysis system",
        parents=[common_parser],
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. init
    subparsers.add_parser("init", parents=[common_parser], help="Initialize workspace directories and default configs")

    # 2. build
    build_parser = subparsers.add_parser("build", parents=[common_parser], help="Phase 1: Build and prepare defect database")
    build_sub = build_parser.add_subparsers(dest="build_action", required=True)

    inspect_p = build_sub.add_parser("inspect", parents=[common_parser], help="Inspect raw source file")
    inspect_p.add_argument("file", type=str, help="Source file (.xlsx or .csv)")

    propose_p = build_sub.add_parser("propose", parents=[common_parser], help="Propose column catalog and normalization maps")
    propose_p.add_argument("file", type=str, help="Source file (.xlsx or .csv)")
    propose_p.add_argument("--sheet", type=str, default=None, help="Sheet name for Excel")
    propose_p.add_argument("--header-row", type=int, default=1, help="Header row index (1-based)")
    propose_p.add_argument("--id-column", type=str, default=None, help="Name of ID column")

    review_p = build_sub.add_parser("review-export", parents=[common_parser], help="Export review queue for agent/human decision")

    finalize_p = build_sub.add_parser("finalize", parents=[common_parser], help="Finalize mappings and build DuckDB and FTS index")
    finalize_p.add_argument("file", type=str, help="Source file (.xlsx or .csv)")
    finalize_p.add_argument("--sheet", type=str, default=None, help="Sheet name for Excel")
    finalize_p.add_argument("--header-row", type=int, default=1, help="Header row index (1-based)")
    finalize_p.add_argument("--id-column", type=str, default=None, help="Name of ID column")
    finalize_p.add_argument("--auto-accept", action="store_true", help="Auto-accept all pending normalization rules")

    validate_p = build_sub.add_parser("validate", parents=[common_parser], help="Validate Phase 1 dataset consistency")
    validate_p.add_argument("file", type=str, help="Source file (.xlsx or .csv)")

    # 3. analyze
    analyze_parser = subparsers.add_parser("analyze", parents=[common_parser], help="Phase 2: Analyze defect database")
    analyze_sub = analyze_parser.add_subparsers(dest="analyze_action", required=True)

    plan_p = analyze_sub.add_parser("plan", parents=[common_parser], help="Validate analysis plan from JSON/YAML or request")
    plan_p.add_argument("--request", type=str, default="", help="Natural language request")
    plan_p.add_argument("--plan-file", type=str, default=None, help="JSON file containing QueryPlan")

    exec_p = analyze_sub.add_parser("execute", parents=[common_parser], help="Execute analysis plan retrieval and batch partitioning")
    exec_p.add_argument("--plan-file", type=str, required=True, help="JSON file containing validated QueryPlan")
    exec_p.add_argument("--question", type=str, default="Analysis", help="Question text")
    exec_p.add_argument("--run-id", type=str, default=None, help="Optional run ID")

    complete_p = analyze_sub.add_parser("complete", parents=[common_parser], help="Complete analysis with agent batch findings and render report")
    complete_p.add_argument("--run-id", type=str, required=True, help="Run ID")
    complete_p.add_argument("--findings-file", type=str, required=True, help="JSON file containing batch findings")

    # 4. audit
    audit_parser = subparsers.add_parser("audit", parents=[common_parser], help="Data quality and landscape audits")
    audit_sub = audit_parser.add_subparsers(dest="audit_action", required=True)
    audit_sub.add_parser("data-quality", parents=[common_parser], help="Run deterministic data quality audit")
    audit_sub.add_parser("landscape", parents=[common_parser], help="Run landscape concentration analysis")

    # 5. license & sbom
    lic_parser = subparsers.add_parser("license", parents=[common_parser], help="Generate SPDX SBOM and License compliance report")

    # 6. feedback
    fb_parser = subparsers.add_parser("feedback", parents=[common_parser], help="Record user feedback and candidate lessons")
    fb_parser.add_argument("--run-id", type=str, required=True, help="Analysis Run ID")
    fb_parser.add_argument("--type", type=str, default="analysis_feedback", help="Feedback type")
    fb_parser.add_argument("--text", type=str, required=True, help="User feedback text")
    fb_parser.add_argument("--lesson", type=str, required=True, help="Derived lesson candidate")

    args = parser.parse_args()
    ws = WorkspaceConfig(args.workspace)

    if args.command == "init":
        res = ws.init_workspace()
        print_output(res, args.json)

    elif args.command == "build":
        pipeline = BuildPipeline(ws)
        if args.build_action == "inspect":
            res = pipeline.inspect(Path(args.file).resolve())
            print_output(res, args.json)
        elif args.build_action == "propose":
            res = pipeline.propose(
                Path(args.file).resolve(),
                sheet_name=args.sheet,
                header_row=args.header_row,
                id_column=args.id_column,
            )
            print_output(res, args.json)
        elif args.build_action == "finalize":
            res = pipeline.finalize_build(
                Path(args.file).resolve(),
                sheet_name=args.sheet,
                header_row=args.header_row,
                id_column=args.id_column,
                auto_accept_all_pending=args.auto_accept,
            )
            print_output(res, args.json)

    elif args.command == "analyze":
        controller = AnalysisController(ws)
        if args.analyze_action == "plan":
            plan_dict = None
            if args.plan_file:
                with open(args.plan_file, "r", encoding="utf-8") as f:
                    plan_dict = json.load(f)
            res = controller.plan_analysis(args.request, plan_dict)
            print_output(res, args.json)
        elif args.analyze_action == "execute":
            with open(args.plan_file, "r", encoding="utf-8") as f:
                plan_dict = json.load(f)
            plan = QueryPlan.from_dict(plan_dict)
            run_id = args.run_id or f"RUN-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            run = controller.execute_retrieval(run_id, args.question, plan)
            out = {
                "run_id": run.run_id,
                "status": run.status,
                "candidate_count": len(run.candidate_ids),
                "batch_count": len(run.batch_items),
                "batches": [b.to_dict() for b in run.batch_items],
                "statistics": run.statistics,
                "trace": run.trace_info,
            }
            print_output(out, args.json)
        elif args.analyze_action == "complete":
            run_id = args.run_id
            ckpt_path = ws.analysis_runs_dir / f"{run_id}.json"
            if not ckpt_path.exists():
                print(f"Error: Run checkpoint '{ckpt_path}' not found.", file=sys.stderr)
                sys.exit(1)
            with open(ckpt_path, "r", encoding="utf-8") as f:
                run_dict = json.load(f)

            plan = QueryPlan.from_dict(run_dict["plan"])
            run = AnalysisRun(run_id, run_dict["question"], plan)
            # Rehydrate candidate IDs
            con = duckdb.connect(str(ws.duckdb_path), read_only=True)
            res_rids = [r[0] for r in con.execute(run_dict["trace_info"]["executed_sql"], run_dict["trace_info"]["sql_params"]).fetchall()]
            con.close()
            run.candidate_ids = res_rids
            run.trace_info = run_dict["trace_info"]
            run.statistics = run_dict.get("statistics", {})

            # Load findings
            with open(args.findings_file, "r", encoding="utf-8") as f:
                findings_data = json.load(f)
                if isinstance(findings_data, dict) and "findings" in findings_data:
                    findings_list = findings_data["findings"]
                else:
                    findings_list = findings_data

            res = controller.complete_analysis(run, findings_list)
            print_output(res, args.json)

    elif args.command == "audit":
        cat_data = ws.load_yaml(ws.columns_config_path)
        from defect_insight.build.column_catalog import ColumnCatalog
        cat = ColumnCatalog.from_dict(cat_data) if cat_data else ColumnCatalog()

        if args.audit_action == "data-quality":
            auditor = DataQualityAuditor(str(ws.duckdb_path), cat)
            res = auditor.run_deterministic_audit()
            print_output(res, args.json)
        elif args.audit_action == "landscape":
            analyzer = LandscapeAnalyzer(str(ws.duckdb_path), cat)
            res = analyzer.analyze_landscape()
            print_output(res, args.json)

    elif args.command == "license":
        sbom_path = generate_spdx_sbom(ws.root)
        rep_path = generate_license_report(ws.root)
        out = {
            "status": "success",
            "sbom_path": str(sbom_path),
            "license_report_path": str(rep_path),
        }
        print_output(out, args.json)

    elif args.command == "feedback":
        ledger = LessonLedger(ws.config_dir / "lessons.yaml")
        recorder = FeedbackRecorder(ledger)
        lesson = recorder.record_feedback(
            run_id=args.run_id,
            feedback_type=args.type,
            user_feedback=args.text,
            derived_lesson=args.lesson,
        )
        print_output(lesson.to_dict(), args.json)


if __name__ == "__main__":
    main()
