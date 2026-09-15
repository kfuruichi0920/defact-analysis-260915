---
name: defect-db-build
description: "Phase 1: Ingests raw defect tables (Excel/CSV), runs profiling, normalizes categories with review flow, builds DuckDB tables and SQLite FTS5 trigram indexes, and generates build and license reports."
---

# Defect DB Build Skill (Phase 1)

## Overview
This skill guides the AI Agent through preparing and building a structured analytical database from raw defect tables (`.xlsx` or `.csv`).
It coordinates deterministic Python CLI operations with Agent semantic judgment and human review.

## Architecture & Principles
- **Separation of Concerns:** Python Engine handles file reading, mechanical cleansing, profiling, database loading, and reporting. The AI Agent handles semantic categorization and mapping ambiguity resolution.
- **No LLM API in Python:** All LLM reasoning is performed directly by the executing Agent in context.
- **Raw Data Preservation:** Raw strings are preserved in `raw_defects` without destructive alteration.

## Workflow

### Step 1: Workspace Initialization & Inspection
Initialize workspace directories and inspect the source file:
```bash
python -m defect_insight.cli init
python -m defect_insight.cli build inspect "<path_to_defect_file>" --json
```
Review detected sheet name, header row index, and sample data.

### Step 2: Deterministic Profiling & Proposal
Generate preliminary Column Catalog, Value Dictionaries, and candidate NormalizeMap:
```bash
python -m defect_insight.cli build propose "<path_to_defect_file>" --json
```
Inspect the output JSON:
- Review inferred Column Roles (`category`, `ordered_category`, `short_text`, `long_text`, `status`, etc.).
- Review `review_queue` items for unknown or low-confidence category mappings.

### Step 3: Semantic Judgment & Review
For items in `config/normalize-map.yaml`:
- Verify that standard phases (UT, IT, ST) map to canonical phase IDs (`phase_unit_test`, `phase_integration`, etc.).
- If any mapping requires user confirmation, present the candidate options clearly to the user.
- Update `config/normalize-map.yaml` and `config/columns.yaml` as necessary.

### Step 4: Finalize Build & FTS Index
Execute database assembly:
```bash
python -m defect_insight.cli build finalize "<path_to_defect_file>" --auto-accept --json
```
This builds:
1. `data/defects.duckdb` (`raw_defects` and `normalized_defects` tables)
2. `data/defects-fts.sqlite` (SQLite FTS5 table with trigram tokenizer)
3. `reports/build-report.md` and `reports/build-report.json`
4. `license-report.md` and `sbom.spdx.json`
5. `exports/*.csv` (normalized data, catalog, map, validation results)

### Step 5: Verification
Ensure no `ERROR` severity validation findings exist in `reports/build-report.md`.
Inform the user when Phase 1 dataset preparation is complete and ready for Phase 2 analysis.
