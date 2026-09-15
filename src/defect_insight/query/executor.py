"""Safe query execution engine combining DuckDB and SQLite FTS5 (Sections 42, 50)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import duckdb
from defect_insight.build.fts_builder import FTSIndexBuilder
from defect_insight.query.compiler import CompiledQuery


class QueryExecutor:
    """Executes compiled queries against DuckDB and SQLite FTS5."""

    def __init__(self, duckdb_path: Path, fts_sqlite_path: Path):
        self.duckdb_path = duckdb_path
        self.fts_sqlite_path = fts_sqlite_path
        self.fts_builder = FTSIndexBuilder(fts_sqlite_path)

    def retrieve_candidate_ids(
        self,
        compiled: CompiledQuery,
        set_operation: str = "INTERSECT",  # INTERSECT (AND), UNION (OR), SQL_ONLY, FTS_ONLY
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Retrieves candidate record IDs combining SQL and FTS filters deterministically.
        
        Returns:
            candidate_ids: List of matching record_ids
            trace_info: Retrieval metrics
        """
        sql_ids: Optional[Set[str]] = None
        fts_ids: Optional[Set[str]] = None

        # 1. Execute SQL filter
        con = duckdb.connect(str(self.duckdb_path), read_only=True)
        try:
            res = con.execute(compiled.sql_query, compiled.sql_params).fetchall()
            sql_ids = {r[0] for r in res}
        finally:
            con.close()

        # 2. Execute FTS lexical search if required
        if compiled.fts_required:
            matched = self.fts_builder.search(
                terms=compiled.fts_terms,
                columns=compiled.fts_columns,
            )
            fts_ids = set(matched)

        # 3. Combine using Set Algebra
        final_set: Set[str] = set()
        if sql_ids is not None and fts_ids is not None:
            if set_operation == "UNION":
                final_set = sql_ids | fts_ids
            else:  # INTERSECT (default AND)
                final_set = sql_ids & fts_ids
        elif sql_ids is not None:
            final_set = sql_ids
        elif fts_ids is not None:
            final_set = fts_ids

        # Sort for determinism
        candidate_ids = sorted(final_set)

        trace_info = {
            "sql_matched_count": len(sql_ids) if sql_ids is not None else 0,
            "fts_matched_count": len(fts_ids) if fts_ids is not None else 0,
            "set_operation": set_operation,
            "final_candidate_count": len(candidate_ids),
        }

        return candidate_ids, trace_info

    def fetch_records_by_ids(
        self,
        record_ids: List[str],
        columns: Optional[List[str]] = None,
        table: str = "normalized_defects",
    ) -> List[Dict[str, Any]]:
        """Fetches records for specified IDs with column projection."""
        if not record_ids:
            return []

        con = duckdb.connect(str(self.duckdb_path), read_only=True)
        try:
            # Build column projection
            if columns:
                # Always ensure record_id is included
                proj_cols = ["record_id"] + [c for c in columns if c != "record_id"]
                col_sql = ", ".join(f'"{c}"' for c in proj_cols)
            else:
                col_sql = "*"

            # Query with temp table or batch for large list
            con.execute("CREATE TEMPORARY TABLE target_ids (rid VARCHAR);")
            con.executemany("INSERT INTO target_ids VALUES (?);", [[rid] for rid in record_ids])

            sql = f"SELECT {col_sql} FROM {table} t JOIN target_ids i ON t.record_id = i.rid ORDER BY t.row_idx ASC;"
            cursor = con.execute(sql)
            col_names = [d[0] for d in cursor.description]
            rows = cursor.fetchall()
            records = [dict(zip(col_names, row)) for row in rows]
        finally:
            con.close()

        return records

    def fetch_raw_evidence_records(self, record_ids: List[str]) -> List[Dict[str, Any]]:
        """Fetches complete raw records for evidence appendix (Section 77, 80)."""
        return self.fetch_records_by_ids(record_ids, columns=None, table="raw_defects")
