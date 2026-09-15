"""Token-aware dynamic batch partitioning and 100% coverage tracking (Sections 59-64)."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple


class BatchItem:
    """Represents a chunk of records prepared for LLM analysis within context budget."""

    def __init__(self, batch_id: str, batch_index: int, total_batches: int, records: List[Dict[str, Any]], estimated_chars: int):
        self.batch_id = batch_id
        self.batch_index = batch_index
        self.total_batches = total_batches
        self.records = records
        self.estimated_chars = estimated_chars
        self.status = "pending"  # pending, completed, failed
        self.findings: List[Dict[str, Any]] = []
        self.error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "batch_index": self.batch_index,
            "total_batches": self.total_batches,
            "record_count": len(self.records),
            "estimated_chars": self.estimated_chars,
            "status": self.status,
            "findings_count": len(self.findings),
            "record_ids": [r["record_id"] for r in self.records],
        }


class BatchManager:
    """Calculates dynamic batches based on character/token budgets and ensures 100% coverage."""

    def __init__(self, context_budget_chars: int = 12000):
        self.context_budget_chars = context_budget_chars

    def create_batches(
        self,
        records: List[Dict[str, Any]],
        projected_columns: List[str],
    ) -> List[BatchItem]:
        """Dynamically partitions records into batches based on actual text size."""
        if not records:
            return []

        # Ensure record_id is included in projection
        cols_to_keep = ["record_id"] + [c for c in projected_columns if c != "record_id"]

        batches: List[List[Dict[str, Any]]] = []
        current_batch: List[Dict[str, Any]] = []
        current_batch_chars = 0

        for rec in records:
            # Projected record representation
            proj_rec = {k: rec.get(k) for k in cols_to_keep if k in rec}
            rec_chars = sum(len(str(v)) for v in proj_rec.values() if v is not None) + 50  # overhead

            # If adding this record exceeds budget and current batch is non-empty
            if current_batch and (current_batch_chars + rec_chars > self.context_budget_chars):
                batches.append(current_batch)
                current_batch = [proj_rec]
                current_batch_chars = rec_chars
            else:
                current_batch.append(proj_rec)
                current_batch_chars += rec_chars

        if current_batch:
            batches.append(current_batch)

        total_b = len(batches)
        batch_items: List[BatchItem] = []
        for idx, b_recs in enumerate(batches, start=1):
            b_id = f"batch-{idx:03d}"
            b_chars = sum(sum(len(str(v)) for v in r.values() if v is not None) for r in b_recs)
            batch_items.append(BatchItem(b_id, idx, total_b, b_recs, b_chars))

        return batch_items

    @staticmethod
    def verify_coverage(
        candidate_ids: List[str],
        batches: List[BatchItem],
    ) -> Dict[str, Any]:
        """Verifies 100% coverage across all batches (Section 59)."""
        candidate_set = set(candidate_ids)
        evaluated_ids: set[str] = set()
        failed_ids: set[str] = set()

        for b in batches:
            b_ids = {r["record_id"] for r in b.records}
            if b.status == "completed":
                evaluated_ids.update(b_ids)
            elif b.status == "failed":
                failed_ids.update(b_ids)

        missing_ids = candidate_set - (evaluated_ids | failed_ids)
        total_candidates = len(candidate_set)
        evaluated_count = len(evaluated_ids)
        failed_count = len(failed_ids)
        skipped_count = len(missing_ids)

        coverage_ratio = (evaluated_count / total_candidates) if total_candidates > 0 else 1.0

        return {
            "total_candidates": total_candidates,
            "evaluated_count": evaluated_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
            "coverage_percentage": round(coverage_ratio * 100, 2),
            "is_100_percent_covered": (total_candidates == evaluated_count and skipped_count == 0 and failed_count == 0),
        }
