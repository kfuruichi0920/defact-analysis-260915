"""Phase 2 CSV Exporters (Sections 74, 100)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List
from defect_insight.build.column_catalog import ColumnCatalog
from defect_insight.evidence.store import EvidenceStore
from defect_insight.evidence.validator import FindingItem


def export_phase2_csvs(
    export_dir: Path,
    catalog: ColumnCatalog,
    filtered_records: List[Dict[str, Any]],
    raw_evidence_records: List[Dict[str, Any]],
    findings: List[FindingItem],
    evidence_store: EvidenceStore,
    statistics: Dict[str, Any],
    semantic_filter_results: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, str]:
    """Exports all Phase 2 analysis artifacts to CSV."""
    export_dir.mkdir(parents=True, exist_ok=True)
    exported_files = {}

    # 1. filtered-records.csv
    f_path = export_dir / "filtered-records.csv"
    if filtered_records:
        headers = list(filtered_records[0].keys())
        with open(f_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(filtered_records)
        exported_files["filtered_records"] = str(f_path)

    # 2. evidence-raw.csv
    e_raw_path = export_dir / "evidence-raw.csv"
    if raw_evidence_records:
        headers = list(raw_evidence_records[0].keys())
        with open(e_raw_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(raw_evidence_records)
        exported_files["evidence_raw"] = str(e_raw_path)

    # 3. insight-evidence.csv (Finding to Record mapping)
    map_path = export_dir / "insight-evidence.csv"
    with open(map_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["finding_id", "finding_type", "evidence_type", "record_id", "claim"])
        for finding in findings:
            for rid in finding.supporting_records:
                writer.writerow([finding.finding_id, finding.finding_type, "supporting", rid, finding.claim])
            for rid in finding.counter_records:
                writer.writerow([finding.finding_id, finding.finding_type, "counter", rid, finding.claim])
    exported_files["insight_evidence"] = str(map_path)

    # 4. statistics.csv
    stat_path = export_dir / "statistics.csv"
    with open(stat_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["dimension", "category", "count", "percentage"])
        dists = statistics.get("distributions", {})
        for dim, rows in dists.items():
            for r in rows:
                writer.writerow([dim, r["value"], r["count"], r.get("percentage", 0)])
    exported_files["statistics"] = str(stat_path)

    # 5. semantic-filter-results.csv (if any)
    if semantic_filter_results:
        sem_path = export_dir / "semantic-filter-results.csv"
        with open(sem_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["record_id", "judgment", "reason"])
            writer.writeheader()
            writer.writerows(semantic_filter_results)
        exported_files["semantic_filter_results"] = str(sem_path)

    return exported_files
