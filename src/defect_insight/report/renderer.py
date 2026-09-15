"""Comprehensive Report Renderer with Evidence Raw Data Appendix (Sections 74-84)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from defect_insight.evidence.store import EvidenceStore
from defect_insight.evidence.validator import FindingItem
from defect_insight.build.column_catalog import ColumnCatalog


class ReportRenderer:
    """Renders structured Markdown and JSON reports without outsourcing raw evidence formatting to LLM."""

    def __init__(self, catalog: ColumnCatalog):
        self.catalog = catalog

    def render_report(
        self,
        run_meta: Dict[str, Any],
        statistics: Dict[str, Any],
        findings: List[FindingItem],
        evidence_store: EvidenceStore,
        raw_evidence_records: List[Dict[str, Any]],
        normalized_evidence_records: List[Dict[str, Any]],
        coverage_info: Dict[str, Any],
        lessons_applied: List[Dict[str, Any]],
        detail_level: str = "detailed",
    ) -> Tuple[Dict[str, Any], str]:
        """Renders standard Markdown report (report.md) and JSON structured artifact (report.json)."""
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        # Prepare JSON structure
        report_json = {
            "run_id": run_meta.get("run_id"),
            "question": run_meta.get("question"),
            "analysis_mode": run_meta.get("analysis_mode"),
            "dataset_version": run_meta.get("dataset_version", "1.0"),
            "generated_at": now_str,
            "coverage": coverage_info,
            "statistics": statistics,
            "findings": [f.to_dict() for f in findings],
            "evidence_count": len(raw_evidence_records),
            "lessons_applied": lessons_applied,
            "execution_trace": run_meta.get("trace", {}),
        }

        # Build Markdown Document (Sections 75-84)
        md: List[str] = [
            f"# Defect Analysis Report: {run_meta.get('run_id', 'RUN')}",
            "",
            f"**Generated:** {now_str}  ",
            f"**Analysis Mode:** `{run_meta.get('analysis_mode')}`  ",
            f"**Dataset Source:** `{run_meta.get('dataset_source', 'defects.duckdb')}`  ",
            f"**Coverage:** {coverage_info.get('coverage_percentage', 100.0)}% ({coverage_info.get('evaluated_count', 0)}/{coverage_info.get('total_candidates', 0)} records evaluated)  ",
            "",
            "---",
            "",
            "## 1. Request",
            f"> {run_meta.get('question', '')}",
            "",
            "## 2. Executive Summary",
        ]

        # Executive Summary deterministically generated from structured findings (Section 76)
        if findings:
            md.append("Key findings identified from candidate records:")
            for f in findings:
                hyp_count = len(f.hypotheses)
                supp_count = len(f.supporting_records)
                count_count = len(f.counter_records)
                md.append(f"- **[{f.finding_type}]** {f.claim} *(Supporting: {supp_count}, Counter: {count_count}, Confidence: {f.confidence})*")
        else:
            md.append("- No specific semantic patterns identified above the confidence threshold.")

        md.extend([
            "",
            "## 3. Analysis Scope & Targets",
            f"- **Analysis Targets:** {', '.join(run_meta.get('analysis_targets', ['cause', 'countermeasure']))}",
            f"- **Prior Analysis Mode:** `{run_meta.get('prior_analysis_mode', 'disabled')}`",
            "",
            "## 4. Analysis Strategy & Retrieval Plan",
            f"- **Set Algebra:** `{run_meta.get('trace', {}).get('set_operation', 'INTERSECT')}`",
            f"- **SQL Query Executed:**",
            f"```sql\n{run_meta.get('trace', {}).get('executed_sql', 'N/A')}\n```",
            f"- **FTS Terms:** {', '.join(run_meta.get('trace', {}).get('fts_terms', [])) if run_meta.get('trace', {}).get('fts_terms') else 'None'}",
            "",
            "## 5. Facts & Deterministic Statistics",
            f"Total Candidates Extracted: **{statistics.get('total_candidates', 0):,} records**",
            "",
        ])

        # Render 1D distributions
        dists = statistics.get("distributions", {})
        for col_id, dist_rows in dists.items():
            col_def = self.catalog.get_column(col_id)
            c_name = col_def.display_name if col_def else col_id
            md.extend([
                f"### Distribution: `{c_name}` ({col_id})",
                "| Value | Count | Percentage |",
                "|---|---|---|",
            ])
            for r in dist_rows[:8]:
                md.append(f"| {r['value']} | {r['count']} | {r['percentage']}% |")
            if len(dist_rows) > 8:
                md.append(f"| ... ({len(dist_rows) - 8} more categories) | | |")
            md.append("")

        # Render Cross tabs
        ctabs = statistics.get("cross_tabs", {})
        for pair_name, rows in ctabs.items():
            md.extend([
                f"### Cross Tabulation: `{pair_name}`",
                "| Category A | Category B | Count |",
                "|---|---|---|",
            ])
            for r in rows[:10]:
                keys = [k for k in r.keys() if k != "count"]
                v1 = r.get(keys[0], "") if len(keys) > 0 else ""
                v2 = r.get(keys[1], "") if len(keys) > 1 else ""
                md.append(f"| {v1} | {v2} | {r['count']} |")
            md.append("")

        # Section 7: Findings
        md.extend([
            "## 7. Findings & Insights",
            "",
        ])
        for idx, f in enumerate(findings, start=1):
            md.extend([
                f"### Finding {idx}: [{f.finding_id}] {f.claim}",
                f"- **Pattern Type:** `{f.finding_type}`",
                f"- **Confidence:** `{f.confidence.upper()}` ({f.confidence_reason})",
                f"- **Supporting Records:** {len(f.supporting_records)} records ({', '.join(f.supporting_records[:5])}{'...' if len(f.supporting_records) > 5 else ''})",
                f"- **Counter Evidence Records:** {len(f.counter_records)} records ({', '.join(f.counter_records) if f.counter_records else 'None detected'})",
                "",
            ])

        # Section 8: Hypotheses
        md.extend([
            "## 8. Preventive Knowledge & Hypotheses",
            "",
        ])
        for idx, f in enumerate(findings, start=1):
            if f.hypotheses:
                md.append(f"**From Finding {idx} ({f.finding_id}):**")
                for hyp in f.hypotheses:
                    md.append(f"- 💡 {hyp}")
                md.append("")

        # Section 9: Counter Evidence & Limitations
        md.extend([
            "## 9. Counter Evidence & Analysis Limitations",
            "",
        ])
        counter_exists = False
        for f in findings:
            if f.counter_records:
                counter_exists = True
                md.append(f"- **Finding [{f.finding_id}] Counter Records:** {', '.join(f.counter_records)}")
                md.append(f"  *Note: These records contradict the primary pattern and represent edge cases or secondary failure modes.*")
        if not counter_exists:
            md.append("- No explicit counter records detected within the candidate population.")

        # Section 10: Evidence Index
        md.extend([
            "",
            "## 10. Evidence Index (Deduplicated)",
            "",
            "| Record ID | Used By Finding IDs |",
            "|---|---|",
        ])
        for rid in evidence_store.all_evidence_record_ids:
            f_ids = ", ".join(f"`{fid}`" for fid in evidence_store.get_findings_for_record(rid))
            md.append(f"| `{rid}` | {f_ids} |")

        # Section 11: Execution Trace
        md.extend([
            "",
            "## 11. Analysis Execution Trace",
            "",
            f"- Candidates Extracted: {run_meta.get('trace', {}).get('final_candidate_count', 0)}",
            f"- SQL Matched: {run_meta.get('trace', {}).get('sql_matched_count', 0)}",
            f"- FTS Matched: {run_meta.get('trace', {}).get('fts_matched_count', 0)}",
            f"- Batch Partitions: {run_meta.get('trace', {}).get('batch_count', 1)}",
            f"- Coverage: {coverage_info.get('coverage_percentage', 100.0)}%",
            f"- Refinement Iterations: {run_meta.get('trace', {}).get('refinements_count', 0)}",
            "",
        ])

        if lessons_applied:
            md.append("### Applied Lessons:")
            for l in lessons_applied:
                md.append(f"- **[{l['lesson_id']}]** {l['derived_lesson']} (Scope: {l.get('scope')})")
            md.append("")

        # Section 12: Evidence Raw Data Appendix (MANDATORY - Section 77-82)
        # All columns, full raw content, no summarization, raw + normalized displayed for normalized fields
        md.extend([
            "---",
            "",
            "## 12. Evidence Raw Data Appendix",
            "",
            "> **Traceability Guarantee:** The table below displays 100% of raw data records supporting or countering the findings in this report, preserving original text without omission, summarization, or compression.",
            "",
        ])

        norm_rec_map = {r["record_id"]: r for r in normalized_evidence_records}

        for r_raw in raw_evidence_records:
            rid = r_raw.get("record_id")
            used_findings = evidence_store.get_findings_for_record(rid)
            r_norm = norm_rec_map.get(rid, {})

            md.extend([
                f"### Record: `{rid}`",
                f"**Source File:** `{r_raw.get('source_file')}` (Row: {r_raw.get('row_idx')})  ",
                f"**Referenced by Findings:** {', '.join(f'`{f}`' for f in used_findings)}  ",
                "",
                "| Column | Raw Content | Normalized Canonical (if applicable) |",
                "|---|---|---|",
            ])

            for c in self.catalog.columns.values():
                col_id = c.column_id
                col_name = c.display_name
                raw_val = r_raw.get(f"{col_id}_raw") or r_raw.get(col_id)
                raw_val_str = str(raw_val).replace("\n", "<br>") if raw_val is not None else "*NULL*"

                if c.capabilities.get("normalizable", False):
                    norm_label = r_norm.get(f"{col_id}_label") or r_norm.get(col_id)
                    norm_val_str = f"`{norm_label}`" if norm_label is not None else "*NULL*"
                else:
                    norm_val_str = "-"

                md.append(f"| **{col_name}** (`{col_id}`) | {raw_val_str} | {norm_val_str} |")

            md.append("")

        return report_json, "\n".join(md)
