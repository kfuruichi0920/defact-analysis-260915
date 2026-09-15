"""Evidence and Finding data models and strict integrity validator (Sections 67-73)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set


class FindingItem:
    """Represents an analytical finding with supporting and counter evidence."""

    def __init__(
        self,
        finding_id: str,
        finding_type: str,  # root_cause_pattern, escape_pattern, countermeasure_pattern, anomaly, etc.
        claim: str,
        supporting_records: List[str],
        counter_records: Optional[List[str]] = None,
        confidence: str = "medium",  # high, medium, low
        confidence_reason: str = "",
        hypotheses: Optional[List[str]] = None,
        derived_batch_ids: Optional[List[str]] = None,
    ):
        self.finding_id = finding_id
        self.finding_type = finding_type
        self.claim = claim
        self.supporting_records = supporting_records
        self.counter_records = counter_records or []
        self.confidence = confidence if confidence in ("high", "medium", "low") else "medium"
        self.confidence_reason = confidence_reason
        self.hypotheses = hypotheses or []
        self.derived_batch_ids = derived_batch_ids or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "finding_type": self.finding_type,
            "claim": self.claim,
            "supporting_records": self.supporting_records,
            "counter_records": self.counter_records,
            "confidence": self.confidence,
            "confidence_reason": self.confidence_reason,
            "hypotheses": self.hypotheses,
            "derived_batch_ids": self.derived_batch_ids,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FindingItem:
        return cls(
            finding_id=data["finding_id"],
            finding_type=data.get("finding_type", "root_cause_pattern"),
            claim=data.get("claim", ""),
            supporting_records=data.get("supporting_records", []),
            counter_records=data.get("counter_records", []),
            confidence=data.get("confidence", "medium"),
            confidence_reason=data.get("confidence_reason", ""),
            hypotheses=data.get("hypotheses", []),
            derived_batch_ids=data.get("derived_batch_ids", []),
        )


class FindingValidationReport:
    """Report for Finding integrity validation."""

    def __init__(self):
        self.accepted_findings: List[FindingItem] = []
        self.rejected_findings: List[Dict[str, Any]] = []

    @property
    def accepted_count(self) -> int:
        return len(self.accepted_findings)

    @property
    def rejected_count(self) -> int:
        return len(self.rejected_findings)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_submitted": self.accepted_count + self.rejected_count,
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "accepted_findings": [f.to_dict() for f in self.accepted_findings],
            "rejected_findings": self.rejected_findings,
        }


def validate_findings(
    findings: List[FindingItem],
    valid_candidate_ids: Set[str],
) -> FindingValidationReport:
    """Strictly validates findings against candidate record database (Section 73)."""
    report = FindingValidationReport()

    for f in findings:
        rejection_reasons = []

        if not f.claim or not f.claim.strip():
            rejection_reasons.append("Finding claim is empty.")

        if not f.supporting_records:
            rejection_reasons.append("Finding lacks supporting records.")
        else:
            # Check if all supporting records exist in candidate set
            missing_supp = [rid for rid in f.supporting_records if rid not in valid_candidate_ids]
            if missing_supp:
                rejection_reasons.append(
                    f"Supporting records not found in candidate set: {missing_supp[:3]} (total missing: {len(missing_supp)})"
                )

        if f.counter_records:
            missing_counter = [rid for rid in f.counter_records if rid not in valid_candidate_ids]
            if missing_counter:
                rejection_reasons.append(
                    f"Counter records not found in candidate set: {missing_counter[:3]} (total missing: {len(missing_counter)})"
                )

        if rejection_reasons:
            report.rejected_findings.append({
                "finding_id": f.finding_id,
                "claim": f.claim,
                "reasons": rejection_reasons,
            })
        else:
            report.accepted_findings.append(f)

    return report
