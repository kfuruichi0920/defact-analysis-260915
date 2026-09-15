"""Evidence index and deduplication store (Sections 81, 82, 83)."""

from __future__ import annotations

from typing import Any, Dict, List, Set
from defect_insight.evidence.validator import FindingItem


class EvidenceStore:
    """Manages relationship between findings and raw evidence records with deduplication."""

    def __init__(self):
        # record_id -> Set of finding_ids
        self.record_to_findings: Dict[str, Set[str]] = {}
        # finding_id -> FindingItem
        self.findings_map: Dict[str, FindingItem] = {}

    def register_findings(self, findings: List[FindingItem]) -> None:
        """Registers validated findings and maps record references."""
        for f in findings:
            self.findings_map[f.finding_id] = f
            for rid in f.supporting_records:
                if rid not in self.record_to_findings:
                    self.record_to_findings[rid] = set()
                self.record_to_findings[rid].add(f.finding_id)
            for rid in f.counter_records:
                if rid not in self.record_to_findings:
                    self.record_to_findings[rid] = set()
                self.record_to_findings[rid].add(f.finding_id)

    @property
    def all_evidence_record_ids(self) -> List[str]:
        """Returns deduplicated list of all evidence record IDs."""
        return sorted(self.record_to_findings.keys())

    def get_findings_for_record(self, record_id: str) -> List[str]:
        return sorted(self.record_to_findings.get(record_id, set()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_unique_evidence_records": len(self.record_to_findings),
            "record_to_findings": {k: sorted(v) for k, v in self.record_to_findings.items()},
        }
