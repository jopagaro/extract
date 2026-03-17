"""
Centralised path resolution for the engine.

All modules resolve paths through this module.
The desktop app or CLI can override roots via environment variables
without touching any logic code.

Environment variables:
    MINING_ENGINE_ROOT      — root of the platform codebase
    MINING_PROJECTS_ROOT    — root of the projects data folder (outside platform)
    MINING_PROMPTS_ROOT     — override location of prompts/ (rarely needed)
    MINING_SCHEMAS_ROOT     — override location of schemas/ (rarely needed)
    MINING_CONFIGS_ROOT     — override location of configs/ (rarely needed)
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Platform roots
# ---------------------------------------------------------------------------

def get_engine_root() -> Path:
    """Root of the mining_intelligence_platform/ codebase."""
    env = os.getenv("MINING_ENGINE_ROOT")
    if env:
        return Path(env).resolve()
    # engine/core/paths.py → up three levels to platform root
    return Path(__file__).resolve().parent.parent.parent


def get_projects_root() -> Path:
    """
    Root of the mining_projects/ data folder.
    Lives outside the platform codebase.
    """
    env = os.getenv("MINING_PROJECTS_ROOT")
    if env:
        return Path(env).resolve()
    # Default: sibling folder named mining_projects next to the platform root
    return get_engine_root().parent / "mining_projects"


def get_prompts_root() -> Path:
    env = os.getenv("MINING_PROMPTS_ROOT")
    if env:
        return Path(env).resolve()
    return get_engine_root() / "prompts"


def get_schemas_root() -> Path:
    env = os.getenv("MINING_SCHEMAS_ROOT")
    if env:
        return Path(env).resolve()
    return get_engine_root() / "schemas"


def get_configs_root() -> Path:
    env = os.getenv("MINING_CONFIGS_ROOT")
    if env:
        return Path(env).resolve()
    return get_engine_root() / "configs"


def get_project_template_root() -> Path:
    return get_engine_root() / "_project_template"


# ---------------------------------------------------------------------------
# Per-project paths
# ---------------------------------------------------------------------------

def project_root(project_id: str) -> Path:
    return get_projects_root() / project_id


def project_raw(project_id: str) -> Path:
    return project_root(project_id) / "raw"


def project_normalized(project_id: str) -> Path:
    return project_root(project_id) / "normalized"


def project_outputs(project_id: str) -> Path:
    return project_root(project_id) / "outputs"


def project_runs(project_id: str) -> Path:
    return project_root(project_id) / "runs"


def project_metadata_file(project_id: str) -> Path:
    return project_normalized(project_id) / "metadata" / "project_metadata.json"


def project_assessments_file(project_id: str) -> Path:
    """The data assessments file written by the critic after each run."""
    return project_normalized(project_id) / "interpreted" / "risk" / "data_assessments.json"


def run_root(project_id: str, run_id: str) -> Path:
    return project_runs(project_id) / run_id


# ---------------------------------------------------------------------------
# Prompt paths
# ---------------------------------------------------------------------------

def system_prompt_file(role: str) -> Path:
    """
    Resolve a system prompt file by role name.
    e.g. role='economics_analyst' → prompts/system/economics_analyst.md
    """
    return get_prompts_root() / "system" / f"{role}.md"


def task_prompt_file(task_category: str, task_name: str) -> Path:
    """
    Resolve a task prompt file.
    e.g. task_category='extraction', task_name='extract_project_facts'
         → prompts/extraction/extract_project_facts.md
    """
    return get_prompts_root() / task_category / f"{task_name}.md"


# ---------------------------------------------------------------------------
# Config paths
# ---------------------------------------------------------------------------

def global_config_file(name: str) -> Path:
    return get_configs_root() / "global" / f"{name}.yaml"


def llm_config_file(name: str) -> Path:
    return get_configs_root() / "llm" / f"{name}.yaml"


def economics_config_file(name: str) -> Path:
    return get_configs_root() / "economics" / f"{name}.yaml"


def price_deck_config_file(scenario: str) -> Path:
    return get_configs_root() / "economics" / "price_decks" / f"{scenario}.yaml"


def fiscal_regime_config_file(jurisdiction: str) -> Path:
    return get_configs_root() / "economics" / "fiscal_regimes" / f"{jurisdiction}.yaml"


# ---------------------------------------------------------------------------
# Schema paths
# ---------------------------------------------------------------------------

def schema_file(category: str, name: str) -> Path:
    return get_schemas_root() / category / f"{name}.schema.json"
