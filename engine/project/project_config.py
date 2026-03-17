"""
Per-project configuration.

Every project has a project_config.yaml stored at:
    <project>/normalized/metadata/project_config.yaml

This config captures the human-supplied facts about a project that the engine
cannot derive from data alone — primary commodity, jurisdiction, study level,
mine type, etc. These values act as defaults and overrides throughout the
engine wherever the data does not explicitly state them.

The config is written once at project creation and updated explicitly via the
CLI or review workflow. Automated engine runs never overwrite it.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from engine.core.enums import MineType, StudyLevel
from engine.core.logging import get_logger
from engine.core.paths import project_normalized

log = get_logger(__name__)

_CONFIG_FILENAME = "project_config.yaml"


@dataclass
class ProjectConfig:
    """
    Per-project configuration values.

    All fields beyond *project_id* are optional at creation — the engine
    operates with defaults and flags missing values as data gaps.
    """

    project_id: str

    # ---- Identity -----------------------------------------------------------
    name: str = ""                    # human-readable project name
    company: str = ""                 # owner / operator company name
    ticker: str = ""                  # stock exchange ticker (if listed)
    location: str = ""                # country or region free text
    jurisdiction: str = ""            # YAML slug for fiscal regime lookup

    # ---- Geology / commodity ------------------------------------------------
    primary_element: str = ""         # e.g. "Au", "Cu", "Li"
    primary_element_unit: str = ""    # grade unit e.g. "g/t", "%", "ppm"
    metal_unit: str = ""              # metal reporting unit e.g. "oz", "t", "lb"
    secondary_elements: list[str] = field(default_factory=list)

    # ---- Study / project stage ----------------------------------------------
    study_level: str = StudyLevel.UNKNOWN.value
    mine_type: str = MineType.OPEN_PIT.value
    project_status: str = ""          # "exploration", "development", "production"

    # ---- Economics defaults -------------------------------------------------
    # Used when the source data does not explicitly state these values
    discount_rate_percent: float = 8.0
    currency: str = "USD"

    # ---- Reporting ----------------------------------------------------------
    classification_system: str = ""   # "NI 43-101", "JORC 2012", "PERC"
    report_language: str = "en"

    # ---- Notes --------------------------------------------------------------
    notes: str = ""

    # =========================================================================
    # Conversion helpers
    # =========================================================================

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ProjectConfig":
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in d.items() if k in known})


# ---------------------------------------------------------------------------
# Read / write
# ---------------------------------------------------------------------------

def _config_path(project_id: str) -> Path:
    return project_normalized(project_id) / "metadata" / _CONFIG_FILENAME


def read_project_config(project_id: str) -> ProjectConfig:
    """
    Load the project config from YAML.

    Returns a default ``ProjectConfig`` if no config file exists yet — this
    lets the engine run before the user has supplied explicit configuration
    while still accurately reporting what is missing.
    """
    path = _config_path(project_id)
    if not path.exists():
        log.debug("No project_config.yaml found for %s — returning defaults", project_id)
        return ProjectConfig(project_id=project_id)
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return ProjectConfig.from_dict(data)


def write_project_config(config: ProjectConfig) -> Path:
    """
    Write (or overwrite) the project_config.yaml for a project.

    Creates parent directories if needed.
    Returns the path written.
    """
    path = _config_path(config.project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(
            config.to_dict(),
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=True,
        )
    log.debug("Project config written: %s", path)
    return path


def update_project_config(project_id: str, **updates: Any) -> ProjectConfig:
    """
    Load the existing config, apply *updates*, write it back, and return
    the updated config.

    Only recognised ``ProjectConfig`` field names are applied — unknown keys
    are silently ignored to prevent config file corruption.
    """
    config = read_project_config(project_id)
    known = set(config.__dataclass_fields__)
    for key, value in updates.items():
        if key in known:
            object.__setattr__(config, key, value)
        else:
            log.warning("Ignoring unknown project config key '%s'", key)
    write_project_config(config)
    return config
