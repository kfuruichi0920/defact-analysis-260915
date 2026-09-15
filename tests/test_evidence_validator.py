"""Unit tests for Finding validation and EvidenceStore deduplication."""

import pytest
from defect_insight.evidence.validator import FindingItem, validate_findings
from defect_insight.evidence.store import EvidenceStore


def test_validate_findings_and_deduplication():
    valid_candidate_ids = {"REC-001", "REC-002", "REC-003", "REC-004"}

    findings = [
        FindingItem(
            finding_id="F-01",
            finding_type="root_cause_pattern",
            claim="タイマー競合のパターン",
            supporting_records=["REC-001", "REC-002"],
            counter_records=["REC-004"],
            confidence="high",
        ),
        FindingItem(
            finding_id="F-02",
            finding_type="root_cause_pattern",
            claim="不正なIDを含むFinding",
            supporting_records=["REC-999"],  # Invalid
            confidence="low",
        ),
    ]

    report = validate_findings(findings, valid_candidate_ids)
    assert report.accepted_count == 1
    assert report.rejected_count == 1
    assert report.accepted_findings[0].finding_id == "F-01"

    # Evidence store deduplication
    store = EvidenceStore()
    store.register_findings(report.accepted_findings)

    assert store.all_evidence_record_ids == ["REC-001", "REC-002", "REC-004"]
    assert store.get_findings_for_record("REC-001") == ["F-01"]
