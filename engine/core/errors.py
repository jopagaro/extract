"""
Custom exception hierarchy for the engine.

All engine exceptions inherit from MiningEngineError so callers can
catch the whole family with a single except clause if needed.
"""


class MiningEngineError(Exception):
    """Base class for all engine errors."""


# ---------------------------------------------------------------------------
# Project / filesystem errors
# ---------------------------------------------------------------------------

class ProjectNotFoundError(MiningEngineError):
    """Raised when a requested project folder does not exist."""


class ProjectAlreadyExistsError(MiningEngineError):
    """Raised when trying to create a project that already exists."""


class SchemaViolationError(MiningEngineError):
    """Raised when a project folder is missing required schema directories."""


# ---------------------------------------------------------------------------
# Configuration errors
# ---------------------------------------------------------------------------

class ConfigNotFoundError(MiningEngineError):
    """Raised when a required config file cannot be located."""


class ConfigValidationError(MiningEngineError):
    """Raised when a config file fails schema or type validation."""


# ---------------------------------------------------------------------------
# Data / normalisation errors
# ---------------------------------------------------------------------------

class DataIngestionError(MiningEngineError):
    """Raised when a raw file cannot be read or parsed."""


class NormalisationError(MiningEngineError):
    """Raised when normalisation of a dataset fails."""


class MissingRequiredFieldError(MiningEngineError):
    """Raised when a field required for a model calculation is absent."""


class ConflictingDataError(MiningEngineError):
    """Raised when two sources provide irreconcilable values for the same field."""


class UnitConversionError(MiningEngineError):
    """Raised when a unit conversion cannot be performed."""


# ---------------------------------------------------------------------------
# LLM errors
# ---------------------------------------------------------------------------

class LLMProviderError(MiningEngineError):
    """Raised when an LLM API call fails."""


class PromptNotFoundError(MiningEngineError):
    """Raised when a required prompt file cannot be found."""


class ExtractionFailedError(MiningEngineError):
    """Raised when LLM extraction does not return parseable structured output."""


# ---------------------------------------------------------------------------
# Run / execution errors
# ---------------------------------------------------------------------------

class RunAlreadyExistsError(MiningEngineError):
    """Raised when trying to create a run ID that already exists."""


class RunNotFoundError(MiningEngineError):
    """Raised when a requested run cannot be found."""


# ---------------------------------------------------------------------------
# Review / override errors
# ---------------------------------------------------------------------------

class OverrideValidationError(MiningEngineError):
    """Raised when a manual override fails schema validation."""
