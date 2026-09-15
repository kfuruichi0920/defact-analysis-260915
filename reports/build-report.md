# Dataset Build Report (Phase 1)

**Dataset Source:** `golden_defects.csv`  
**Source SHA-256:** `3ed329e462045981d941ee876eae1a73f161a2b53374dd377762a69e6ebbe687`  
**Built At:** 2026-09-15 15:59:07 UTC  
**Total Records:** 50  
**Total Columns:** 12  
**Validation Status:** ✅ PASSED (No Errors)  

## 1. Column Catalog & Profiling Summary

| Column ID | Display Name | Inferred Role | Null Ratio | Distinct Count | Capabilities |
|---|---|---|---|---|---|
| `defect_id` | 管理番号 | `record_id` | 0.0% | 50 | filterable, searchable |
| `title` | タイトル | `short_text` | 0.0% | 50 | filterable, searchable |
| `detect_phase` | 検出工程 | `ordered_category` | 0.0% | 9 | filterable, aggregatable, normalizable, ordered |
| `injection_phase` | 混入工程 | `ordered_category` | 0.0% | 4 | filterable, aggregatable, normalizable, ordered |
| `severity` | 重要度 | `category` | 0.0% | 3 | filterable, aggregatable, normalizable |
| `defect_type` | 不具合分類 | `category` | 0.0% | 5 | filterable, aggregatable, normalizable |
| `cause` | 原因 | `long_text` | 0.0% | 50 | searchable |
| `escape_cause` | 流出原因 | `long_text` | 0.0% | 50 | searchable |
| `countermeasure` | 対策 | `long_text` | 0.0% | 50 | searchable |
| `assignee` | 担当者 | `category` | 0.0% | 50 | filterable, aggregatable, normalizable |
| `detect_date` | 検出日 | `date` | 0.0% | 50 | filterable, aggregatable, ordered |
| `status` | 状態 | `status` | 0.0% | 1 | filterable, aggregatable, normalizable |

## 2. Normalization Mapping Summary

### Column: `検出工程` (detect_phase)
Total Mapped Rules: 9

| Raw Value | Canonical ID | Canonical Label | Ordinal | Status | Source |
|---|---|---|---|---|---|
| UT | `phase_unit_test` | 単体試験 | 40 | accepted | dictionary_match |
| 結合試験 | `phase_integration` | 結合試験 | 50 | accepted | dictionary_match |
| ST | `phase_system` | システム試験 | 60 | accepted | dictionary_match |
| IT | `phase_integration` | 結合試験 | 50 | accepted | dictionary_match |
| 単体 | `phase_unit_test` | 単体試験 | 40 | accepted | dictionary_match |
| 単体試験 | `phase_unit_test` | 単体試験 | 40 | accepted | dictionary_match |
| 総合 | `phase_system` | システム試験 | 60 | accepted | dictionary_match |
| システム試験 | `phase_system` | システム試験 | 60 | accepted | dictionary_match |
| 結合 | `phase_integration` | 結合試験 | 50 | accepted | dictionary_match |

### Column: `混入工程` (injection_phase)
Total Mapped Rules: 4

| Raw Value | Canonical ID | Canonical Label | Ordinal | Status | Source |
|---|---|---|---|---|---|
| 詳細設計 | `phase_detail_design` | 詳細設計 | 30 | accepted | dictionary_match |
| コーディング | `phase_coding` | 実装・単体作成 | 35 | accepted | dictionary_match |
| 実装 | `phase_coding` | 実装・単体作成 | 35 | accepted | dictionary_match |
| 基本設計 | `phase_basic_design` | 基本設計 | 20 | accepted | dictionary_match |

### Column: `重要度` (severity)
Total Mapped Rules: 3

| Raw Value | Canonical ID | Canonical Label | Ordinal | Status | Source |
|---|---|---|---|---|---|
| 高 | `val_高` | 高 | - | accepted | unknown_value |
| 低 | `val_低` | 低 | - | accepted | unknown_value |
| 中 | `val_中` | 中 | - | accepted | unknown_value |

### Column: `不具合分類` (defect_type)
Total Mapped Rules: 5

| Raw Value | Canonical ID | Canonical Label | Ordinal | Status | Source |
|---|---|---|---|---|---|
| 機能不全 | `val_機能不全` | 機能不全 | - | accepted | unknown_value |
| タイミング/排他 | `val_タイミング/排他` | タイミング/排他 | - | accepted | unknown_value |
| 境界値 | `val_境界値` | 境界値 | - | accepted | unknown_value |
| UI不備 | `val_ui不備` | UI不備 | - | accepted | unknown_value |
| メモリリーク | `val_メモリリーク` | メモリリーク | - | accepted | unknown_value |

### Column: `担当者` (assignee)
Total Mapped Rules: 50

| Raw Value | Canonical ID | Canonical Label | Ordinal | Status | Source |
|---|---|---|---|---|---|
| 佐藤 | `val_佐藤` | 佐藤 | - | accepted | unknown_value |
| 鈴木 | `val_鈴木` | 鈴木 | - | accepted | unknown_value |
| 高橋 | `val_高橋` | 高橋 | - | accepted | unknown_value |
| 田中 | `val_田中` | 田中 | - | accepted | unknown_value |
| 渡辺 | `val_渡辺` | 渡辺 | - | accepted | unknown_value |
| 伊藤 | `val_伊藤` | 伊藤 | - | accepted | unknown_value |
| 山本 | `val_山本` | 山本 | - | accepted | unknown_value |
| 中村 | `val_中村` | 中村 | - | accepted | unknown_value |
| 小林 | `val_小林` | 小林 | - | accepted | unknown_value |
| 加藤 | `val_加藤` | 加藤 | - | accepted | unknown_value |
| 吉田 | `val_吉田` | 吉田 | - | accepted | unknown_value |
| 山田 | `val_山田` | 山田 | - | accepted | unknown_value |
| 佐々木 | `val_佐々木` | 佐々木 | - | accepted | unknown_value |
| 山口 | `val_山口` | 山口 | - | accepted | unknown_value |
| 松本 | `val_松本` | 松本 | - | accepted | unknown_value |
| ... (35 more rules) | | | | | |

### Column: `状態` (status)
Total Mapped Rules: 2

| Raw Value | Canonical ID | Canonical Label | Ordinal | Status | Source |
|---|---|---|---|---|---|
| 完了 | `val_完了` | 完了 | - | accepted | unknown_value |
| 2025-04-18 | `val_2025-04-18` | 2025-04-18 | - | accepted | unknown_value |

## 3. Lexical Search (SQLite FTS5) Index

- **FTS Provider:** SQLite FTS5 (trigram tokenizer)
- **Indexed Records:** 50
- **Indexed Columns:** `title`, `cause`, `escape_cause`, `countermeasure`

## 4. Validation Findings

- Errors: 0
- Warnings: 0
- Info: 2

- ℹ️ **[INFO]** (fts): FTS index verified: 50 records cleanly indexed.
- ℹ️ **[INFO]** (structure): Total records verified: 50, total columns: 12

## 5. Generated Artifacts

- `data/defects.duckdb`: Analytical columnar database
- `data/defects-fts.sqlite`: FTS5 lexical search database
- `exports/normalized-data.csv`: Normalized records export
- `exports/column-catalog.csv`: Column catalog export
- `exports/normalize-map.csv`: Complete normalization dictionary export
- `exports/validation-results.csv`: Validation findings log
- `license-report.md`: Software license compliance verification
- `sbom.spdx.json`: SPDX 2.3 software bill of materials