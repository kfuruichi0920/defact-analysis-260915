"""Workspace configuration and path resolution for defect-insight."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml


class WorkspaceConfig:
    """Manages workspace directories and configuration files."""

    def __init__(self, root: Optional[Path | str] = None):
        if root is None:
            # Default to current working directory or DEFECT_INSIGHT_WORKSPACE
            env_ws = os.environ.get("DEFECT_INSIGHT_WORKSPACE")
            self.root = Path(env_ws).resolve() if env_ws else Path.cwd().resolve()
        else:
            self.root = Path(root).resolve()

        # Workspace standard directory structure (Section 6)
        self.source_dir = self.root / "source"
        self.config_dir = self.root / "config"
        self.data_dir = self.root / "data"
        self.state_dir = self.root / "state"
        self.reports_dir = self.root / "reports"
        self.exports_dir = self.root / "exports"
        self.runs_dir = self.root / "runs"
        self.build_runs_dir = self.runs_dir / "build"
        self.analysis_runs_dir = self.runs_dir / "analysis"
        self.skills_dir = self.root / "skills"

        # Standard config file paths
        self.dataset_config_path = self.config_dir / "dataset.yaml"
        self.columns_config_path = self.config_dir / "columns.yaml"
        self.column_map_path = self.config_dir / "column-map.yaml"
        self.normalize_map_path = self.config_dir / "normalize-map.yaml"
        self.value_dictionaries_path = self.config_dir / "value-dictionaries.yaml"
        self.analysis_defaults_path = self.config_dir / "analysis-defaults.yaml"

        # Database paths
        self.duckdb_path = self.data_dir / "defects.duckdb"
        self.fts_sqlite_path = self.data_dir / "defects-fts.sqlite"
        self.history_duckdb_path = self.state_dir / "analysis-history.duckdb"

    def init_workspace(self) -> Dict[str, Any]:
        """Initializes directory structure and default templates if they don't exist."""
        dirs = [
            self.source_dir,
            self.config_dir,
            self.data_dir,
            self.state_dir,
            self.reports_dir,
            self.exports_dir,
            self.build_runs_dir,
            self.analysis_runs_dir,
            self.skills_dir / "defect-db-build",
            self.skills_dir / "defect-analysis",
        ]
        created_dirs = []
        for d in dirs:
            if not d.exists():
                d.mkdir(parents=True, exist_ok=True)
                created_dirs.append(str(d))

        # Default analysis-defaults.yaml
        if not self.analysis_defaults_path.exists():
            default_analysis = {
                "default_mode": "filtered_analysis",
                "evidence_level": "detailed",
                "max_refinements": 3,
                "context_budget_chars": 12000,
                "token_batch_margin": 0.2,
                "data_egress": {
                    "external_llm_api": False,
                    "use_current_agent": True,
                    "minimize_columns": True,
                },
            }
            self.save_yaml(self.analysis_defaults_path, default_analysis)

        return {
            "root": str(self.root),
            "created_dirs": created_dirs,
            "status": "ready",
        }

    @staticmethod
    def load_yaml(path: Path) -> Dict[str, Any]:
        """Safely loads a YAML file."""
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}

    @staticmethod
    def save_yaml(path: Path, data: Any) -> None:
        """Saves data to a YAML file with proper indentation."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
