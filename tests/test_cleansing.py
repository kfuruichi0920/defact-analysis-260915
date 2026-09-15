"""Unit tests for mechanical cleansing and search shadow text."""

import pytest
from defect_insight.build.cleansing import clean_mechanical_text, clean_search_shadow_text


def test_clean_mechanical_text_unicode_nfkc():
    # Full-width alphanumerics and kana normalization
    raw = "　ＴＥＳＴ　１２３　ﾃｽﾄ　"
    cleaned = clean_mechanical_text(raw)
    assert cleaned == "TEST 123 テスト"


def test_clean_mechanical_text_whitespace_and_newlines():
    raw = " line 1 \r\n\r\n  line 2   with   spaces  \n"
    cleaned = clean_mechanical_text(raw)
    assert cleaned == "line 1\n\nline 2 with spaces"


def test_clean_mechanical_text_preserves_semantics():
    # Long narrative text must not be summarized or altered
    narrative = "通信制御スレッドにおいてタイマー満了イベントと再送完了コールの競合が発生した。"
    cleaned = clean_mechanical_text(narrative)
    assert cleaned == narrative


def test_clean_mechanical_text_empty_and_none():
    assert clean_mechanical_text(None) is None
    assert clean_mechanical_text("") is None
    assert clean_mechanical_text("   \n \t  ") is None


def test_clean_search_shadow_text():
    raw = " Ｔｉｍｅｏｕｔ 発生 "
    shadow = clean_search_shadow_text(raw)
    assert shadow == "timeout 発生"
