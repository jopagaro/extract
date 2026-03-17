"""
Shared enums used across the entire engine.

All string values are lowercase-with-underscores so they serialise cleanly
to JSON and match config file keys without transformation.
"""

from enum import StrEnum


class DataStatus(StrEnum):
    """State of a data field or dataset."""
    PRESENT = "present"
    PARTIAL = "partial"
    MISSING = "missing"
    CONFLICTING = "conflicting"
    UNVERIFIABLE = "unverifiable"


class EconomicDirection(StrEnum):
    """
    Economic implication of a data state.
    No numeric scale — direction only. The assessment paragraph carries the detail.
    """
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class LLMProvider(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class LLMRole(StrEnum):
    """Which system role prompt to load before a task."""
    BASE = "base"
    GEOLOGY_ANALYST = "geology_analyst"
    ECONOMICS_ANALYST = "economics_analyst"
    REPORT_WRITER = "report_writer"
    DATA_EXTRACTOR = "data_extractor"
    CRITIC = "critic"


class LLMTask(StrEnum):
    """High-level task category — maps to prompts/ subfolder."""
    EXTRACTION = "extraction"
    SUMMARIZATION = "summarization"
    REPORTING = "reporting"
    CRITIQUE = "critique"
    SCORING = "scoring"


class ProjectStatus(StrEnum):
    SCAFFOLD_ONLY = "scaffold_only"
    INGESTING = "ingesting"
    NORMALIZING = "normalizing"
    ANALYZING = "analyzing"
    REVIEWING = "reviewing"
    COMPLETE = "complete"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    PARTIAL = "partial"


class Severity(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ReportFormat(StrEnum):
    MARKDOWN = "markdown"
    DOCX = "docx"
    PDF = "pdf"


class StudyLevel(StrEnum):
    SCOPING = "scoping"
    PEA = "pea"
    PFS = "pfs"
    FS = "fs"
    HISTORICAL = "historical"
    UNKNOWN = "unknown"


class MineType(StrEnum):
    OPEN_PIT = "open_pit"
    UNDERGROUND = "underground"
    OPEN_PIT_AND_UNDERGROUND = "open_pit_and_underground"
    HEAP_LEACH = "heap_leach"
    IN_SITU = "in_situ"
    PLACER = "placer"
    OTHER = "other"
