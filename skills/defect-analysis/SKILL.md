---
name: defect-analysis
description: "Phase 2: Performs deterministic and semantic analysis on prepared defect datasets. Converts questions into QueryPlans, runs SQL/FTS retrieval, ensures 100% batch coverage, extracts findings with counter evidence, and generates reports with full raw evidence appendix."
---

# Defect Analysis Skill (Phase 2)

## Overview
This skill guides the AI Agent through answering user analytical inquiries regarding past defects.
It enforces deterministic statistics first, token-efficient dynamic batching, strict evidence traceability, and counter evidence verification.

## Core Rules & Guardrails
1. **Never generate free-form SQL from Agent:** Always create structured `QueryPlan` adhering to the catalog schema and allowed operators.
2. **Deterministic Statistics First:** Never ask LLM to calculate counts or percentages; use the numbers computed by Python Engine.
3. **Coverage 100% in Filtered Analysis:** All candidate records must be evaluated across batches without sampling.
4. **Evidence Raw Data Appendix:** Finding evidence raw text must be output in full without summarization, omission, or compression.
5. **Counter Evidence:** Actively search for and report counter examples or edge cases.

## Workflow

### Step 1: Understand Question & Formulate QueryPlan
Interpret user intent and create a temporary `query_plan.json`:
```json
{
  "analysis_mode": "filtered_analysis",
  "filters": [
    {
      "column_id": "detect_phase",
      "operator": "gte",
      "value": "phase_integration"
    }
  ],
  "lexical_search": {
    "required": true,
    "columns": ["title", "cause"],
    "primary_terms": ["タイムアウト"],
    "expanded_terms": ["timeout", "タイマ満了"]
  },
  "projections": ["defect_id", "title", "cause", "escape_cause", "countermeasure", "detect_phase"]
}
```

Validate the plan against the Python engine:
```bash
python -m defect_insight.cli analyze plan --plan-file query_plan.json --json
```

### Step 2: Deterministic Retrieval & Batch Partitioning
Execute retrieval to extract candidate IDs, calculate baseline statistics, and generate token-aware dynamic batches:
```bash
python -m defect_insight.cli analyze execute --plan-file query_plan.json --question "<User_Question>" --json
```
Review:
- `candidate_count`
- `statistics` (distributions and cross-tabs)
- `batches`

### Step 3: Batch Reasoning & Hypothesis Generation
For each batch, examine the projected records and identify:
- Root cause patterns (`root_cause_pattern`)
- Escape mechanisms (`escape_pattern`)
- Countermeasure patterns (`countermeasure_pattern`)
- Supporting Record IDs (must be valid candidate IDs)
- Counter Evidence Record IDs (records where the pattern does not apply or contradicted)
- Confidence (`high`, `medium`, `low`) and reasoning
- Preventive hypotheses and recommendations

Create a `findings.json` file:
```json
{
  "findings": [
    {
      "finding_id": "FIND-001",
      "type": "root_cause_pattern",
      "claim": "非同期処理におけるタイマー満了時の排他制御不備による競合状態",
      "supporting_records": ["REC-0001-xxxx", "REC-0004-yyyy"],
      "counter_records": ["REC-0008-zzzz"],
      "confidence": "high",
      "confidence_reason": "結合試験以降で多発しており、全数統計およびバッチ検証で一致",
      "hypotheses": [
        "状態遷移設計時にタイマーキャンセルと完了イベントの同時発生ケースを網羅する設計チェックリストを導入すべき",
        "通信制御モジュールの共通排他ロックユーティリティを見直す"
      ]
    }
  ]
}
```

### Step 4: Complete Analysis & Render Report
Submit findings to the controller:
```bash
python -m defect_insight.cli analyze complete --run-id "<run_id>" --findings-file findings.json --json
```
This performs:
1. Coverage 100% verification.
2. Finding validation (checks that all supporting/counter IDs exist in candidate set).
3. Deduplicated EvidenceStore registration.
4. Rendering of `reports/<run_id>-report.md` with complete Raw Evidence Appendix (all columns, raw text intact).
5. Generation of `exports/<run_id>/*.csv` artifacts.

### Step 5: User Presentation & Feedback Loop
- Present the executive summary and key findings to the user.
- Direct user to the generated report Markdown for full evidence.
- If the user provides feedback or corrections, record candidate lessons:
```bash
python -m defect_insight.cli feedback --run-id "<run_id>" --type "retrieval_feedback" --text "<User_Feedback>" --lesson "<Derived_Lesson>" --json
```
