# 不具合管理表 AI 分析システム (defect-insight) 実装計画

## 1. 概要と基本アーキテクチャ

本計画は、仕様書（全117項）に基づき、再現性・トークン効率・Evidence Traceability・生データ尊重を徹底した**不具合管理表 AI 分析システム（defect-insight）**をゼロから構築するための詳細設計・実装ステップです。

```
+-----------------------------------------------------------------------------------+
|                              AI Agent (Antigravity)                              |
|   +--------------------------------+       +----------------------------------+   |
|   |   defect-db-build Skill        |       |      defect-analysis Skill       |   |
|   | (Meaning Judgment, Review UI)  |       | (Plan Gen, Semantics, Synthesis) |   |
|   +--------------------------------+       +----------------------------------+   |
+-----------------------------------▲---------------------------------▲-------------+
                                    | CLI (--json)                     | CLI (--json)
+-----------------------------------▼---------------------------------▼-------------+
|                           Python Engine (defect-insight)                          |
|                                                                                   |
|  [Phase 1: Build / Prepare]                [Phase 2: Analyze / Use]               |
|  - Raw Importer (CSV/XLSX)                 - QueryPlan Validator & Compiler       |
|  - Profiler & Column Catalog               - Deterministic Statistics First       |
|  - Mechanical Cleansing                    - Lexical Search (SQLite FTS5 trigram) |
|  - NormalizeMap & Ordered Dict             - Token-aware Batcher & Coverage 100%  |
|  - DuckDB Loader & FTS Builder             - Evidence Validator & Store           |
|  - Validator & Build Report                - Trace & Checkpoint / Resume Engine   |
|  - License & SBOM Generator                - Report & Raw Appendix Renderer       |
+-----------------------------------+---------------------------------+-------------+
                                    |                                 |
+-----------------------------------▼---------------------------------▼-------------+
|                                Storage Layer                                      |
|  - source/ (Raw CSV/XLSX)                  - state/ (Analysis History / Runs)     |
|  - data/defects.duckdb (Raw + Normalized)  - config/ (Catalog, Maps, Dicts)       |
|  - data/defects-fts.sqlite (FTS5 Trigram)  - reports/ & exports/ (Markdown, CSV)  |
+-----------------------------------------------------------------------------------+
```

---

## 2. 採用ライブラリと商用ライセンス方針

仕様書第5項・第114項に基づき、外部LLM APIクライアント（openai, anthropic, google-generativeai 等）は**一切導入しません**。また全依存関係の商用利用可否を検証します。

| パッケージ | バージョン想定 | ライセンス | 商用利用 | 用途 |
|---|---|---|---|---|
| `duckdb` | 最新安定版 (>=1.1.0) | MIT | 可 | 分析用カラムナDB、SQL集計、生データ・正規化データ保持 |
| `openpyxl` | 最新安定版 | MIT | 可 | Excel (.xlsx) ファイル読み込み |
| `pyyaml` | 最新安定版 | MIT | 可 | 設定・Catalog・NormalizeMap・QueryPlan 定義入出力 |
| `sqlite3` | Python 3.12 組み込み | Public Domain | 可 | SQLite FTS5 (trigram) 日本語全文検索 |
| `pytest` | 9.1.1 (導入済み) | MIT | 可 | 単体テスト・結合テスト |

---

## 3. ワークスペースおよびパッケージ構成

仕様書第6項・第102項・第103項に準拠した構成とします。

```text
defact-analysis-260915/
├─ pyproject.toml
├─ README.md
├─ IMPLEMENTATION_PLAN.md
├─ WALKTHROUGH.md
├─ src/
│   └─ defect_insight/
│       ├─ __init__.py
│       ├─ cli.py                         # CLI エントリポイント
│       ├─ config.py                      # ワークスペースパス・設定管理
│       ├─ build/
│       │   ├─ __init__.py
│       │   ├─ importer.py                # CSV/XLSX 読み込み (生データ保持)
│       │   ├─ profiler.py                # 決定論的プロファイリング & Role候補算出
│       │   ├─ column_catalog.py          # Column Catalog 定義・検証
│       │   ├─ cleansing.py               # 機械的クレンジング (NFKC, 空白, 改行等)
│       │   ├─ normalization.py           # NormalizeMap 生成・適用・整合性検査
│       │   ├─ dictionary.py              # Ordered Value Dictionary 管理
│       │   ├─ fts_builder.py             # SQLite FTS5 trigram インデックス構築
│       │   └─ validator.py               # Phase 1 整合性バリデータ
│       ├─ query/
│       │   ├─ __init__.py
│       │   ├─ schema.py                  # QuestionTemplate / QueryPlan スキーマ
│       │   ├─ validator.py               # QueryPlan バリデータ (許可列・演算子)
│       │   ├─ compiler.py                # Set Algebra / SQL / FTS コンパイラ
│       │   └─ executor.py                # DuckDB / SQLite 実行エンジン
│       ├─ analysis/
│       │   ├─ __init__.py
│       │   ├─ controller.py              # 分析パイプライン統合 & Checkpoint
│       │   ├─ statistics.py              # 決定論的統計・クロス集計・時系列
│       │   ├─ batcher.py                 # Token-aware Batch 分割 & 100% Coverage
│       │   ├─ case.py                    # case_investigation 実装
│       │   ├─ filtered.py                # filtered_analysis 実装
│       │   ├─ landscape.py               # landscape_analysis 実装
│       │   └─ quality.py                 # data_quality_analysis 実装
│       ├─ evidence/
│       │   ├─ __init__.py
│       │   ├─ validator.py               # Finding / Evidence 整合性バリデータ
│       │   └─ store.py                   # Evidence / Raw Record 追跡ストア
│       ├─ learning/
│       │   ├─ __init__.py
│       │   ├─ feedback.py                # ユーザーフィードバック受取
│       │   └─ lessons.py                 # Lesson 管理 (candidate/accepted/rejected/retired)
│       ├─ report/
│       │   ├─ __init__.py
│       │   ├─ renderer.py                # Markdown / JSON レポート生成
│       │   └─ exports.py                 # CSV エクスポート各種
│       └─ provenance/
│           ├─ __init__.py
│           ├─ metadata.py                # 再現性メタデータ記録
│           └─ license.py                 # SBOM / License Report 生成
├─ skills/
│   ├─ defect-db-build/
│   │   └─ SKILL.md                       # Phase 1: DB構築・Review用スキル
│   └─ defect-analysis/
│       └─ SKILL.md                       # Phase 2: 分析・検索・レポート用スキル
├─ tests/
│   ├─ test_cleansing.py
│   ├─ test_profiler_catalog.py
│   ├─ test_normalization.py
│   ├─ test_fts_builder.py
│   ├─ test_query_compiler.py
│   ├─ test_statistics.py
│   ├─ test_batcher_coverage.py
│   ├─ test_evidence_validator.py
│   ├─ test_report_renderer.py
│   ├─ test_checkpoint_resume.py
│   ├─ test_golden_dataset_e2e.py        # 50〜100件のゴールデンデータ検証
│   └─ data/
│       └─ golden_defects.csv
```

---

## 4. 段階的実装ステップ

仕様書第113項の推奨実装順序に従い、着実に進めます。

### ステップ 1: 環境セットアップ & 基盤構築
- `duckdb`, `openpyxl`, `pyyaml` のインストールとライセンス確認。
- `pyproject.toml` 作成およびパッケージ骨格整備。
- `provenance/license.py` を実装し、SPDX SBOM (`sbom.spdx.json`) と `license-report.md` 生成機能を作成。
- CLI 骨格 (`cli.py`)、設定管理 (`config.py`) の実装。

### ステップ 2〜9: Phase 1 (Build / Prepare)
- **Importer & Storage**: CSV / XLSX の安全な読み込み、生データそのままの保持、安定 `__record_id` の自動付与。
- **Profiling & Column Catalog**: 欠損率、Distinct数、文字列長、日付/数値パース率、Role推定 (record_id, date, numeric, category, ordered_category, short_text, long_text, status, ignore) および Capability (filterable, searchable, aggregatable, normalizable, ordered)。
- **Cleansing**: Unicode正規化 (NFKC)、空白/改行正規化、全角半角正規化。自由記述の意味破壊禁止。
- **NormalizeMap & Canonical Value**: DISTINCT+COUNT からの未確定値抽出、既存辞書・文字列類似度提案、Human Review キュー出力 (`review-export`) と確定 (`finalize`)。
- **Ordered Value Dictionary**: 順序付きカテゴリ（工程など）の ordinal 定義。
- **DuckDB & SQLite FTS5**: 正規化データおよび生データを DuckDB に格納。SQLite FTS5 (trigram) による各テキスト列の独立インデックス構築。
- **Phase 1 Validation & Build Report**: ERROR/WARNING/INFO 検証、`build-report.md` / `build-report.json`、各種 CSV 出力。

### ステップ 10〜19: Phase 2 (Analyze / Use)
- **Question Template & QueryPlan**: 自由質問から構造化 QueryPlan へのスキーマ定義。
- **QueryPlan Validator & Compiler**: 許可演算子 (eq, neq, in, lt, between, contains 等) と Set Algebra (AND, OR, UNION, INTERSECT, EXCEPT) を安全な SQL および FTS クエリへ変換。任意SQLの直接投入禁止。
- **Retrieval & Semantic Filter**: SQL + FTS による決定論的絞り込み。Agent 向け Semantic Filter (MATCH, NO_MATCH, UNCERTAIN 3値判定プロトコル)。Prepared DB への書き込み禁止。
- **Deterministic Statistics First**: Candidate Records に対する全数集計、カテゴリ分布、時系列推移、クロス集計を Python で計算。
- **Token-aware Batcher & Coverage 100%**: filtered_analysis における全数評価保証、Context Budget を考慮した文字数ベースの動的バッチ分割、LLM Input Projection。
- **Finding & Counter Evidence**: Supporting Records と Counter Records の探索、Facts / Findings / Hypotheses の分離、定性 Confidence (high/medium/low)。
- **Finding Validator**: Evidence ID 実在確認、件数整合性、反例整合性検証。
- **Report & Raw Evidence Appendix**: Finding 根拠となった生データを全件・全列出力（要約・省略・言い換え禁止）、重複排除インデックス、Markdown / JSON レポート出力。
- **Checkpoint / Resume & Trace**: 中断再開可能な Run 状態管理 (`state/analysis-history.duckdb`)、完全な Analysis Trace 記録。

### ステップ 20〜21: Feedback / Learning & Skills & E2E検証
- **Feedback & Lessons**: Feedback Ledger、Lesson ライフサイクル (candidate, accepted, rejected, retired)、Priority 制御（Candidate による除外禁止）。
- **Skills 実装**: `skills/defect-db-build/SKILL.md`, `skills/defect-analysis/SKILL.md`。Agent が Python CLI と対話しながら判断・レビュー・分析を行うワークフロー定義。
- **Golden Dataset & E2E テスト**:
  - 50〜100件の人工不具合データセット作成。
  - `UT → 単体試験` の正規化、自由記述の保持、NULLの非推測、SQL/FTS検索精度、Coverage 100%、Raw Evidence 全列出力、反例検出、Checkpoint/Resume、Candidate Lesson 非除外の自動テスト。

---

## 5. 検証計画 (Verification Plan)

### 自動テスト
```powershell
# 単体テスト・結合テスト実行
pytest -v tests/

# ゴールデンデータセット E2E テスト
pytest -v tests/test_golden_dataset_e2e.py
```

### CLI / E2E 動作確認
1. `defect-insight build inspect` -> `propose` -> `finalize` -> `validate` の一連の Phase 1 実行と `build-report.md`, `defects.duckdb`, `defects-fts.sqlite` の生成確認。
2. `defect-insight analyze plan` -> `execute` の Phase 2 実行と `report.md`, Raw Evidence Appendix, 各種 CSV の整合性確認。
3. `defect-insight audit data-quality` および `landscape` の動作確認。
4. `sbom.spdx.json` および `license-report.md` のライセンス検証確認。
