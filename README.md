# 不具合管理表 AI 分析システム (defect-insight)

長期間蓄積されたソフトウェア不具合管理表（Excel / CSV）から、新規開発・品質改善・設計改善に有用な知見を抽出するためのAI支援分析システムです。

---

## 1. システム概要と設計思想

本システムは、数千〜数万件の不具合管理表を「LLMに全文投入して回答させる」システムではありません。

**「SQL・全文検索・決定論的統計処理を最大限活用して分析対象を決定論的に絞り込み、意味判断が必要な部分だけをAI Agentへ渡し、その判断を根拠生データ（Raw Record）まで完全に追跡・再現できる基盤」** です。

### コア原則
1. **Phase 1 (DB構築) と Phase 2 (分析・活用) の明確な分離**:
   - Phase 1 で構造化カラムナDB（DuckDB）および日本語全文検索インデックス（SQLite FTS5 trigram）を決定論的に構築。
   - Phase 2 で生成済みDBに対して質問・検索・分析を実施。
2. **生データ尊重 (Raw Data Preservation)**:
   - 自由記述（原因・対策・現象等）の改変・要約・省略を厳禁。
   - 分析レポートには根拠となった生データを全件・全列出力（Evidence Raw Data Appendix）。
3. **外部LLM API非依存**:
   - Python Engine 内から OpenAI / Anthropic / Gemini 等の外部APIを直接呼び出しません。
   - 確率的な意味判断は、現在対話中の AI Agent（Antigravity等）が CLI / JSON プロトコルを介して担当します。
4. **トークン効率 & 100% Coverage**:
   - 質問に不要な列を削る Column Projection と、文字量ベースの動的バッチ分割によりコンテキスト予算を遵守。
   - 条件付き集合分析（`filtered_analysis`）では、サンプリングを排して 100% 全数評価を保証。
5. **商用ライセンス遵守**:
   - 商用利用可能な OSS（DuckDB, openpyxl, PyYAML 等）のみ採用。SPDX 2.3 SBOM およびライセンスレポートを自動生成。

---

## 2. 動作環境とセットアップ

### 前提環境
- OS: Windows / macOS / Linux
- Python: 3.10 以上 (Python 3.12 動作確認済み)

### 依存ライブラリのインストール
```bash
pip install duckdb>=1.1.0 openpyxl>=3.1.0 pyyaml>=6.0.0 pytest>=8.0.0
```

またはパッケージを編集可能モードでインストール：
```bash
pip install -e .
```

---

## 3. ディレクトリ構造

```text
defact-analysis-260915/
├─ source/                         # 原本ファイル (CSV, Excel)
│   ├─ sample_defects.csv          # すぐに試せるサンプルCSV (50件)
│   └─ sample_defects.xlsx         # サンプルExcel (50件)
├─ config/                         # カタログ・マッピング・設定ファイル
│   ├─ dataset.yaml
│   ├─ columns.yaml                # Column Catalog (型, Role, Capability)
│   ├─ normalize-map.yaml          # 表記揺れ正規化マップ (UT -> 単体試験 等)
│   ├─ value-dictionaries.yaml     # 順序付きカテゴリ辞書 (開発フェーズ順序等)
│   └─ analysis-defaults.yaml
├─ data/                           # 生成データベース
│   ├─ defects.duckdb              # 主分析カラムナDB (raw_defects + normalized_defects)
│   └─ defects-fts.sqlite          # 全文検索DB (SQLite FTS5 trigram)
├─ state/                          # 分析履歴・Run状態
├─ reports/                        # 生成レポート (Markdown, JSON)
├─ exports/                        # CSVエクスポート
├─ runs/                           # Checkpoint 保存領域
│   ├─ build/
│   └─ analysis/
├─ skills/                         # AI Agent 用スキル定義
│   ├─ defect-db-build/SKILL.md    # Phase 1: DB構築支援スキル
│   └─ defect-analysis/SKILL.md    # Phase 2: 分析・検索支援スキル
├─ src/defect_insight/             # Python Engine 実装
└─ tests/                          # 単体テスト & ゴールデンデータセット E2E テスト
```

---

## 4. クイックスタート (CLI利用手順)

付属のサンプルデータ (`source/sample_defects.csv` または `source/sample_defects.xlsx`) を用いて、DB構築から分析レポート出力までの一連の流れを実行できます。

### ステップ 0: ワークスペース初期化 & ライセンス確認
```bash
# ワークスペース構造を初期化
python -m defect_insight.cli init --json

# 依存パッケージの商用ライセンス検証 & SPDX 2.3 SBOM 生成
python -m defect_insight.cli license --json
```
成果物: `license-report.md`, `sbom.spdx.json`

---

### ステップ 1: 原本ファイルの検査 (Inspect)
原本ファイルを取り込む前に、ヘッダー行やシート名、列の自動検出を確認します。
```bash
python -m defect_insight.cli build inspect source/sample_defects.xlsx --json
```

---

### ステップ 2: 列プロファイリング & 正規化案の生成 (Propose)
決定論的プロファイリングを実行し、列の役割（Role）や表記揺れの候補を抽出します。
```bash
python -m defect_insight.cli build propose source/sample_defects.xlsx --id-column 管理番号 --json
```
- `config/columns.yaml`: 各列の Role（`record_id`, `date`, `ordered_category`, `long_text` 等）が提案されます。
- `config/normalize-map.yaml`: `UT` → `単体試験`, `結合` → `結合試験` などの標準辞書マッチングや類似度候補が生成されます。

---

### ステップ 3: データベースの構築・確定 (Finalize)
マッピングを確定し、DuckDB と SQLite FTS5 インデックスを生成します。
```bash
python -m defect_insight.cli build finalize source/sample_defects.xlsx --id-column 管理番号 --auto-accept --json
```
- `data/defects.duckdb`: 生データテーブル `raw_defects` および正規化テーブル `normalized_defects` が作成されます。
- `data/defects-fts.sqlite`: 日本語 trigram トークナイザによる列分離型全文検索インデックスが作成されます。
- `reports/build-report.md`: ビルド詳細レポートが出力されます。
- `exports/`: 正規化データ、列カタログ、マッピング辞書の CSV がエクスポートされます。

---

### ステップ 4: データ品質監査 & 全体傾向分析 (Audit)
不具合管理表そのものの品質（空欄率、原因と流出原因の重複記載、「注意する」等の表層的対策）や、工程・分類の集中傾向を決定論的に分析します。
```bash
# データ品質監査
python -m defect_insight.cli audit data-quality --json

# 全体傾向 (Landscape) 分析
python -m defect_insight.cli audit landscape --json
```

---

### ステップ 5: 分析の実行 (Phase 2: Analyze)

#### 5.1 Analysis Plan の作成と検証
質問意図に基づき、構造化された `plan.json` を作成します（任意SQLの直接投入は禁止され、許可演算子のみで検証されます）。

例 (`my_plan.json`):
```json
{
  "analysis_mode": "filtered_analysis",
  "filters": [
    {
      "column_id": "detect_phase",
      "operator": "gte",
      "value": 50
    }
  ],
  "lexical_search": {
    "required": true,
    "columns": ["title", "cause"],
    "primary_terms": ["タイマー"],
    "expanded_terms": ["ウォッチドッグ"]
  },
  "projections": ["defect_id", "title", "cause", "escape_cause", "countermeasure", "detect_phase"]
}
```

プランの妥当性をチェック：
```bash
python -m defect_insight.cli analyze plan --plan-file my_plan.json --json
```

#### 5.2 決定論的データ抽出とバッチ分割 (Execute)
SQLと全文検索を合成（INTERSECT等）して候補を抽出し、事前統計を計算した上で、トークン予算に応じた動的バッチを作成します。
```bash
python -m defect_insight.cli analyze execute --plan-file my_plan.json --question "結合試験以降で発生したタイマー関連不具合の分析" --run-id RUN-001 --json
```

#### 5.3 意味判断の反映とレポート生成 (Complete)
AI Agent が各バッチの内容を吟味し、支持レコード・反例レコード（Counter Evidence）・改善仮説を含む `findings.json` を作成して分析を完了します。

例 (`my_findings.json`):
```json
{
  "findings": [
    {
      "finding_id": "FIND-001",
      "type": "root_cause_pattern",
      "claim": "非同期処理におけるタイマー満了イベントと再送処理の排他制御不備",
      "supporting_records": ["DEF-0001", "DEF-0004", "DEF-0008", "DEF-0024"],
      "counter_records": ["DEF-0011"],
      "confidence": "high",
      "confidence_reason": "結合試験以降で多発しており全数集計結果と一致",
      "hypotheses": [
        "タイマーキャンセルとイベント受信の競合を防ぐ共通同期ユーティリティを設計標準化すべき"
      ]
    }
  ]
}
```

分析完了とレポート出力：
```bash
python -m defect_insight.cli analyze complete --run-id RUN-001 --findings-file my_findings.json --json
```

出力される成果物:
- `reports/RUN-001-report.md`: エグゼクティブサマリ、事実・統計、発見事項、反例、**全列生データ Evidence Appendix** を含む完全レポート。
- `exports/RUN-001/`: `filtered-records.csv`, `evidence-raw.csv`, `insight-evidence.csv`, `statistics.csv`。

---

## 5. AI Agent (Skills) との対話連携

Antigravity などの AI Agent とペアプログラミング・分析を行う場合、`skills/` ディレクトリ配下の Skill を通じて対話的に進めることができます。

1. **`defect-db-build` Skill**:
   - 原本ファイルの取り込みから、表記揺れレビューの確認、DBビルドまでを Agent が対話的に誘導します。
2. **`defect-analysis` Skill**:
   - ユーザーの自由な質問（「結合試験で多発している排他制御関連の根本原因は？」など）から、QuestionTemplate と QueryPlan を自動立案し、全数バッチ評価と反例探索を経て、詳細レポートを提示します。

---

## 6. テストの実行

ゴールデンデータセットを用いたエンドツーエンド統合テストを含む全自動テストを実行できます。

```powershell
$env:PYTHONPATH="src"; pytest -v tests/
```

### 主なテスト項目
- `test_cleansing.py`: Unicode (NFKC) 正規化、空白処理、自由記述の意味保持
- `test_profiler_catalog.py`: 列型・Role自動推定、カタログ整合性
- `test_normalization.py`: `UT` → `単体試験` の正規化、順序付きカテゴリ辞書
- `test_fts_builder.py`: SQLite FTS5 trigram による日本語全文検索
- `test_query_compiler.py`: QueryPlan バリデーション、安全な SQL パラメータ化コンパイル
- `test_batcher_coverage.py`: 文字数予算による動的バッチ分割、Coverage 100% 保証
- `test_evidence_validator.py`: Finding バリデータ、重複排除 EvidenceStore
- `test_golden_dataset_e2e.py`: 50件のリアル不具合データを用いた Phase 1 〜 Phase 2 全体フロー検証
