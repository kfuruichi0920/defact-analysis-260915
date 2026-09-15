"""Data quality auditing and landscape analysis engines (Sections 46, 47, 65)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
import duckdb
from defect_insight.build.column_catalog import ColumnCatalog


class DataQualityAuditor:
    """Stage A Deterministic Quality Audit for defect tables (Section 47)."""

    def __init__(self, duckdb_path: str, catalog: ColumnCatalog):
        self.duckdb_path = duckdb_path
        self.catalog = catalog

    def run_deterministic_audit(self) -> Dict[str, Any]:
        """Calculates deterministic data quality metrics across all columns."""
        con = duckdb.connect(self.duckdb_path, read_only=True)
        try:
            total_records = con.execute("SELECT COUNT(*) FROM normalized_defects;").fetchone()[0]

            column_quality: Dict[str, Any] = {}
            for col in self.catalog.columns.values():
                col_id = col.column_id
                # Null count
                sql_null = f'SELECT COUNT(*) FROM normalized_defects WHERE "{col_id}" IS NULL OR "{col_id}" = \'\';'
                null_cnt = con.execute(sql_null).fetchone()[0]
                null_pct = (null_cnt / total_records * 100.0) if total_records > 0 else 0.0

                # Distinct count
                sql_dist = f'SELECT COUNT(DISTINCT "{col_id}") FROM normalized_defects WHERE "{col_id}" IS NOT NULL;'
                dist_cnt = con.execute(sql_dist).fetchone()[0]

                # Text length stats if text
                len_stats = {}
                if col.role in ("short_text", "long_text"):
                    sql_len = f"""
                        SELECT MIN(LENGTH("{col_id}")), MAX(LENGTH("{col_id}")), AVG(LENGTH("{col_id}"))
                        FROM normalized_defects
                        WHERE "{col_id}" IS NOT NULL AND "{col_id}" != '';
                    """
                    row = con.execute(sql_len).fetchone()
                    len_stats = {
                        "min_len": row[0] or 0,
                        "max_len": row[1] or 0,
                        "avg_len": round(row[2] or 0, 1),
                    }

                column_quality[col_id] = {
                    "display_name": col.display_name,
                    "role": col.role,
                    "null_count": null_cnt,
                    "null_percentage": round(null_pct, 2),
                    "distinct_count": dist_cnt,
                    "length_stats": len_stats,
                }

            # Check: Cause vs Escape Cause identical match
            identical_cause_escape = 0
            has_cause = self.catalog.get_column("cause")
            has_escape = self.catalog.get_column("escape_cause")
            if has_cause and has_escape:
                sql_identical = """
                    SELECT COUNT(*)
                    FROM normalized_defects
                    WHERE cause IS NOT NULL AND escape_cause IS NOT NULL
                      AND cause != '' AND cause = escape_cause;
                """
                identical_cause_escape = con.execute(sql_identical).fetchone()[0]

            # Superficial countermeasure checks (e.g. "注意する", "周知する")
            superficial_countermeasures = 0
            has_cm = self.catalog.get_column("countermeasure")
            if has_cm:
                sql_superficial = """
                    SELECT COUNT(*)
                    FROM normalized_defects
                    WHERE countermeasure IS NOT NULL
                      AND (countermeasure LIKE '%注意%' OR countermeasure LIKE '%周知%' OR countermeasure LIKE '%徹底%');
                """
                superficial_countermeasures = con.execute(sql_superficial).fetchone()[0]

            audit_result = {
                "total_records": total_records,
                "column_quality": column_quality,
                "identical_cause_and_escape_cause_count": identical_cause_escape,
                "superficial_countermeasure_keywords_count": superficial_countermeasures,
            }
        finally:
            con.close()

        return audit_result


class LandscapeAnalyzer:
    """Landscape analysis: global distributions, anomaly detection, and concentration (Sections 46, 65)."""

    def __init__(self, duckdb_path: str, catalog: ColumnCatalog):
        self.duckdb_path = duckdb_path
        self.catalog = catalog

    def analyze_landscape(self) -> Dict[str, Any]:
        con = duckdb.connect(self.duckdb_path, read_only=True)
        try:
            total_records = con.execute("SELECT COUNT(*) FROM normalized_defects;").fetchone()[0]

            # Phase concentration
            phase_concentration: List[Dict[str, Any]] = []
            phase_col = self.catalog.get_column("detect_phase") or self.catalog.get_column("injection_phase")
            if phase_col:
                sql = f"""
                    SELECT COALESCE("{phase_col.column_id}_label", "{phase_col.column_id}", '(NULL)') as phase,
                           COUNT(*) as cnt,
                           ROUND(COUNT(*) * 100.0 / {total_records}, 2) as pct
                    FROM normalized_defects
                    GROUP BY 1
                    ORDER BY cnt DESC;
                """
                rows = con.execute(sql).fetchall()
                phase_concentration = [{"phase": r[0], "count": r[1], "percentage": r[2]} for r in rows]

            # Defect Type concentration
            type_concentration: List[Dict[str, Any]] = []
            type_col = self.catalog.get_column("defect_type")
            if type_col:
                sql = f"""
                    SELECT COALESCE("{type_col.column_id}_label", "{type_col.column_id}", '(NULL)') as dtype,
                           COUNT(*) as cnt,
                           ROUND(COUNT(*) * 100.0 / {total_records}, 2) as pct
                    FROM normalized_defects
                    GROUP BY 1
                    ORDER BY cnt DESC;
                """
                rows = con.execute(sql).fetchall()
                type_concentration = [{"defect_type": r[0], "count": r[1], "percentage": r[2]} for r in rows]

            return {
                "total_records": total_records,
                "phase_concentration": phase_concentration,
                "defect_type_concentration": type_concentration,
            }
        finally:
            con.close()
