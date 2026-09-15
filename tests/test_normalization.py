"""Unit tests for NormalizeMap, Dictionary, and Canonical resolution."""

import pytest
from defect_insight.build.dictionary import create_standard_phase_dictionary
from defect_insight.build.normalization import generate_normalization_candidates, ColumnNormalizeMap, NormalizeMapping


def test_standard_phase_dictionary_resolution():
    phase_dict = create_standard_phase_dictionary("dict_phase")
    
    # Aliases
    ut = phase_dict.resolve("UT")
    assert ut is not None
    assert ut.canonical_id == "phase_unit_test"
    assert ut.label == "単体試験"
    assert ut.ordinal == 40

    it = phase_dict.resolve("結合テスト")
    assert it is not None
    assert it.canonical_id == "phase_integration"
    assert it.ordinal == 50


def test_generate_normalization_candidates():
    phase_dict = create_standard_phase_dictionary("dict_phase")
    distinct_counts = {
        "UT": 50,
        "単体": 30,
        "結合試験": 20,
        "新フェーズ未定義": 5,
    }

    nmap, queue = generate_normalization_candidates(
        "detect_phase", distinct_counts, value_dict=phase_dict
    )

    # UT should be resolved to phase_unit_test
    can_id, label, ord_val = nmap.get_canonical("UT")
    assert can_id == "phase_unit_test"
    assert label == "単体試験"
    assert ord_val == 40

    # Unknown category queued for review
    assert any(q["raw_value"] == "新フェーズ未定義" for q in queue)
