"""Deterministic statistical calculations and cross-tabulations (Sections 57, 58, 65)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import duckdb
from defect_insight.build.column_catalog import ColumnCatalog, ColumnDefinition


class DeterministicStatistics:
    """Computes deterministic distributions, trends, and cross-tabulations without LLM."""

    def __init__(self, duckdb_path: str):
        self.duckdb_path = duckdb_path

    def compute_candidate_statistics(
        self,
        candidate_ids: List[str],
        catalog: ColumnCatalog,
        cross_pairs: Optional[List[Tuple[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Calculates comprehensive deterministic statistics for candidate records."""
        if not candidate_ids:
            return {
                "total_candidates": 0,
                "distributions": {},
                "cross_tabs": {},
                "time_trends": {},
            }

        con = duckdb.connect(self.duckdb_path, read_only=True)
        try:
            con.execute("CREATE TEMPORARY TABLE c_ids (rid VARCHAR);")
            con.executemany("INSERT INTO c_ids VALUES (?);", [[rid] for rid in candidate_ids])

            # Base candidate count
            total_count = len(candidate_ids)

            # 1. 1D Distributions for categories and ordered categories
            distributions: Dict[str, Any] = {}
            for col in catalog.columns.values():
                if col.capabilities.get("aggregatable", False):
                    # Check distinct distribution
                    sql = f"""
                        SELECT COALESCE("{col.column_id}_label", "{col.column_id}", '(NULL)') as val,
                               COUNT(*) as cnt,
                               ROUND(COUNT(*) * 100.0 / {total_count}, 2) as pct
                        FROM normalized_defects t
                        JOIN c_ids i ON t.record_id = i.rid
                        GROUP BY 1
                        ORDER BY cnt DESC;
                    """
                    try:
                        rows = con.execute(sql).fetchall()
                        distributions[col.column_id] = [
                            {"value": r[0], "count": r[1], "percentage": r[2]}
                            for r in rows
                        ]
                    except duckdb.Error:
                        pass

            # 2. Cross tabulations (Meaningful pairs only, Section 58)
            meaningful_pairs: List[Tuple[str, str]] = cross_pairs or []
            if not cross_pairs:
                # Select sensible default combinations based on available columns
                candidates = [
                    ("detect_phase", "defect_type"),
                    ("injection_phase", "detect_phase"),
                    ("severity", "detect_phase"),
                    ("component", "defect_type"),
                ]
                for c1, c2 in candidates:
                    if catalog.get_column(c1) and catalog.get_column(c2):
                        meaningful_pairs.append((c1, c2))

            cross_tabs: Dict[str, Any] = {}
            for c1, c2 in meaningful_pairs:
                pair_key = f"{c1}_x_{c2}"
                sql = f"""
                    SELECT COALESCE("{c1}_label", "{c1}", '(NULL)') as row_val,
                           COALESCE("{c2}_label", "{c2}", '(NULL)') as col_val,
                           COUNT(*) as cnt
                    FROM normalized_defects t
                    JOIN c_ids i ON t.record_id = i.rid
                    GROUP BY 1, 2
                    ORDER BY cnt DESC;
                """
                try:
                    rows = con.execute(sql).fetchall()
                    cross_tabs[pair_key] = [
                        {c1: r[0], c2: r[1], "count": r[2]}
                        for r in rows
                    ]
                except duckdb.Error:
                    pass

            # 3. Date Trends (if date column exists)
            time_trends: Dict[str, Any] = {}
            for col in catalog.columns.values():
                if col.role == "date":
                    sql = f"""
                        SELECT SUBSTRING(CAST("{col.column_id}" AS VARCHAR), 1, 7) as ym,
                               COUNT(*) as cnt
                        FROM normalized_defects t
                        JOIN c_ids i ON t.record_id = i.rid
                        WHERE "{col.column_id}" IS NOT NULL AND "{col.column_id}" != ''
                        GROUP BY 1
                        ORDER BY 1 ASC;
                    """
                    try:
                        rows = con.execute(sql).fetchall()
                        time_trends[col.column_id] = [{"year_month": r[0], "count": r[1]} for r in rows]
                    except duckdb.Error:
                        pass

        finally:
            con.close()

        return {
            "total_candidates": total_count,
            "distributions": distributions,
            "cross_tabs": cross_tabs,
            "time_trends": time_trends,
        }
