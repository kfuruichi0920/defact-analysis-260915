"""Unit tests for Token-aware dynamic batcher and 100% coverage verification."""

import pytest
from defect_insight.analysis.batcher import BatchManager


def test_batch_partitioning_and_coverage():
    bm = BatchManager(context_budget_chars=500)

    # 10 records with text
    records = [
        {"record_id": f"REC-{i:03d}", "title": f"Title {i}", "cause": "長い原因説明文です。" * 5}
        for i in range(1, 11)
    ]
    candidate_ids = [r["record_id"] for r in records]

    batches = bm.create_batches(records, projected_columns=["title", "cause"])
    assert len(batches) > 1  # Successfully partitioned

    # Before completion: 0% coverage
    cov_init = bm.verify_coverage(candidate_ids, batches)
    assert cov_init["coverage_percentage"] == 0.0
    assert cov_init["is_100_percent_covered"] is False

    # Complete all batches
    for b in batches:
        b.status = "completed"

    cov_done = bm.verify_coverage(candidate_ids, batches)
    assert cov_done["coverage_percentage"] == 100.0
    assert cov_done["is_100_percent_covered"] is True
    assert cov_done["evaluated_count"] == 10
