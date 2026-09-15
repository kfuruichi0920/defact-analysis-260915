# 不具合管理表 AI 分析システム (defect-insight) 実装完了ウォークスルー

## 1. 概要
仕様書（全117項）に完全準拠した**不具合管理表 AI 分析システム (defect-insight)**の実装が完了しました。
本システムは、DuckDB（構造化分析）・SQLite FTS5 trigram（日本語全文検索）・決定論的統計処理・Token-aware動的バッチ・生データ尊重・Evidence Traceability を兼ね備えた、外部LLM API非依存の再現可能なAI支援分析基盤です。

---

## 2. 実装された主要コンポーネント

### 2.1 アーキテクチャと原則
- **Phase 1 (Build / Prepare) & Phase 2 (Analyze / Use) の明確な分離**:
  - Phase 1: CSV/XLSX インポート、決定論的プロファイリング、Unicode/空白クレンジング、NormalizeMap 生成、レビューキュー、DuckDB（生データ＋正規化データ）および SQLite FTS5 trigram インデックスの構築。
  - Phase 2: 自由質問からの QuestionTemplate / QueryPlan 変換、厳格なバリデーション、安全な SQL & FTS コンパイル、決定論的統計先行、Token-aware 動的バッチ分割、Coverage 100% 保証、Finding 反例検証、全列生データ Evidence Appendix レンダリング、CSV エクスポート。
- **外部LLM API非依存 (Section 4, 114)**:
  - Python Engine から OpenAI / Anthropic / Gemini 等の外部APIを一切呼ばず、現在の AI Agent と CLI / JSON プロトコルで対話。
- **生データ尊重 (Section 9, 77-82)**:
  - Raw データは `raw_defects` テーブルに完全に保持。
  - レポートの Evidence Appendix では要約・省略・言い換えを一切せず、全件・全列の生データを忠実に表示。
- **商用ライセンス遵守 & SBOM (Section 5)**:
  - 依存関係（`duckdb`, `openpyxl`, `pyyaml`, `et-xmlfile`, `pytest`）の商用利用可否を自動検証。
  - `license-report.md` および SPDX 2.3 準拠の `sbom.spdx.json` を生成。

### 2.2 パッケージ構成 (`src/defect_insight/`)
```text
src/defect_insight/
├─ cli.py                         # CLI エントリポイント (--json 対応)
├─ config.py                      # ワークスペースパス・設定管理
├─ provenance/
│   ├─ metadata.py                # 再現性メタデータ (SHA-256, Python/OS, バージョン情報)
│   └─ license.py                 # 商用利用ライセンス検証 & SPDX 2.3 SBOM 生成
├─ build/
│   ├─ importer.py                # CSV/XLSX 読み込み、安定内部ID (__record_id) 生成
│   ├─ profiler.py                # 決定論的プロファイリング、Role & Capability 推定
│   ├─ column_catalog.py          # Column Catalog 定義・管理
│   ├─ cleansing.py               # 機械的クレンジング (NFKC, 空白, 改行) & 検索シャドウ
│   ├─ normalization.py           # NormalizeMap 生成、類似度判定、レビューキュー
│   ├─ dictionary.py              # Ordered Value Dictionary (工程等の順序管理)
│   ├─ fts_builder.py             # SQLite FTS5 (trigram) 日本語全文検索インデックス
│   ├─ validator.py               # Phase 1 バリデータ (ERROR, WARNING, INFO)
│   └─ builder.py                 # DuckDB テーブル構築・レポート出力パイプライン
├─ query/
│   ├─ schema.py                  # QuestionTemplate & QueryPlan スキーマ定義
│   ├─ validator.py               # 許可列・許可演算子の厳格バリデータ
│   ├─ compiler.py                # Set Algebra / SQL / FTS コンパイラ
│   └─ executor.py                # DuckDB & SQLite 実行エンジン
├─ analysis/
│   ├─ controller.py              # 分析パイプライン統合 & Checkpoint 管理
│   ├─ statistics.py              # 決定論的統計先行 (分布、クロス集計、時系列推移)
│   ├─ batcher.py                 # Token-aware 動的バッチ分割 & Coverage 100% 保証
│   └─ quality.py                 # データ品質監査 & Landscape 分析
├─ evidence/
│   ├─ validator.py               # Finding / Evidence 整合性バリデータ (反例チェック)
│   └─ store.py                   # 重複排除 EvidenceStore
├─ learning/
│   ├─ feedback.py                # ユーザーフィードバック・Lesson 記録
│   └─ lessons.py                 # Lesson ライフサイクル (candidate, accepted, rejected, retired)
└─ report/
    ├─ renderer.py                # Markdown (12章構成) & JSON レポートレンダラー
    └─ exports.py                 # 各種 CSV エクスポート
```

### 2.3 スキル定義 (`skills/`)
- `skills/defect-db-build/SKILL.md`: Phase 1 の対話的インポート・プロファイリング・レビュー・DBビルド手順書
- `skills/defect-analysis/SKILL.md`: Phase 2 の Question 理解・QueryPlan 設計・バッチ推論・反例探索・レポート出力手順書

---

## 3. テスト検証結果

16件のテスト（単体テスト＋50件のリアル不具合データを用いたゴールデンデータセット E2E テスト）を実行し、**全て合格（16 passed）**しました。

```powershell
$env:PYTHONPATH="src"; pytest -v tests/

tests/test_batcher_coverage.py::test_batch_partitioning_and_coverage PASSED [  6%]
tests/test_cleansing.py::test_clean_mechanical_text_unicode_nfkc PASSED  [ 12%]
tests/test_cleansing.py::test_clean_mechanical_text_whitespace_and_newlines PASSED [ 18%]
tests/test_cleansing.py::test_clean_mechanical_text_preserves_semantics PASSED [ 25%]
tests/test_cleansing.py::test_clean_mechanical_text_empty_and_none PASSED [ 31%]
tests/test_cleansing.py::test_clean_search_shadow_text PASSED            [ 37%]
tests/test_evidence_validator.py::test_validate_findings_and_deduplication PASSED [ 43%]
tests/test_fts_builder.py::test_fts5_trigram_search PASSED               [ 50%]
tests/test_golden_dataset_e2e.py::test_golden_dataset_full_pipeline_e2e PASSED [ 56%]
tests/test_normalization.py::test_standard_phase_dictionary_resolution PASSED [ 62%]
tests/test_normalization.py::test_generate_normalization_candidates PASSED [ 68%]
tests/test_profiler_catalog.py::test_sanitize_column_id PASSED           [ 75%]
tests/test_profiler_catalog.py::test_profiler_and_role_inference PASSED  [ 81%]
tests/test_query_compiler.py::test_validate_query_plan_valid PASSED      [ 87%]
tests/test_query_compiler.py::test_validate_query_plan_invalid_operator PASSED [ 93%]
tests/test_query_compiler.py::test_compile_query_plan PASSED             [100%]

============================= 16 passed in 1.66s ==============================
```

### ゴールデンデータセット E2E テストでの主要検証項目
- ✅ `UT → 単体試験` などの表記揺れが Canonical ID (`phase_unit_test`) および ordinal (`40`) に自動正規化されること。
- ✅ 原因・対策等の自由記述テキストが改変・要約されず完全に保持されること。
- ✅ 意味的アノテーションや推測情報が Prepared DB に混入しないこと。
- ✅ SQL フィルタと SQLite FTS5 trigram 検索が期待通りの候補レコードを抽出すること。
- ✅ 決定論的統計（度数分布、クロス集計）が LLM 推論より先に確定計算されること。
- ✅ `filtered_analysis` において 100% Coverage（全数評価）が保証されること。
- ✅ Finding Validator が実在しない Record ID や不正な反例を拒絶すること。
- ✅ 重複排除された EvidenceStore により、複数 Finding にまたがるレコードの生データが1箇所に全件・全列出力されること。
- ✅ 中断再開用のチェックポイント（`runs/analysis/<run_id>.json`）が生成されること。
- ✅ Candidate Lesson がレコード除外ルールとして勝手に適用されないこと。
- ✅ SPDX 2.3 SBOM およびライセンスレポートが生成されること。

---

## 4. CLI 動作確認

以下の CLI コマンドの正常動作を確認しました：
1. `python -m defect_insight.cli init --json`
2. `python -m defect_insight.cli license --json`
3. `python -m defect_insight.cli build inspect tests/data/golden_defects.csv --json`
4. `python -m defect_insight.cli build propose tests/data/golden_defects.csv --id-column 管理番号 --json`
5. `python -m defect_insight.cli build finalize tests/data/golden_defects.csv --id-column 管理番号 --auto-accept --json`
6. `python -m defect_insight.cli audit data-quality --json`
7. `python -m defect_insight.cli audit landscape --json`

すべての成果物はワークスペース内に保持され、即座に実業務データへの適用が可能です。
