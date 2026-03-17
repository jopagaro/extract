"""
Geological data models.

These types represent the normalised geological picture of a project.
They are built from raw drillhole, assay, and resource data and serve
as the source of truth for everything downstream — including the
production schedule that feeds the economics engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Drillhole data
# ---------------------------------------------------------------------------

@dataclass
class Collar:
    """A drillhole collar — the surface location and basic metadata."""
    hole_id: str
    easting: float | None
    northing: float | None
    elevation: float | None
    azimuth: float | None        # degrees from north
    dip: float | None            # degrees below horizontal (negative = downward)
    total_depth_m: float | None
    drill_date: str | None = None
    drill_type: str | None = None  # RC, DD, AC, RAB
    program: str | None = None
    notes: str | None = None


@dataclass
class SurveyPoint:
    """A downhole survey measurement at a given depth."""
    hole_id: str
    depth_m: float
    azimuth: float
    dip: float


@dataclass
class AssayInterval:
    """A single assay interval within a drillhole."""
    hole_id: str
    from_m: float
    to_m: float
    length_m: float
    primary_element: str          # e.g. "Au", "Cu", "Li"
    primary_grade: float | None   # in grade_unit
    grade_unit: str               # "g/t", "%", "ppm"
    secondary_grades: dict[str, float] = field(default_factory=dict)
    sample_id: str | None = None
    lab: str | None = None
    flags: list[str] = field(default_factory=list)  # QC flags


@dataclass
class LithologyInterval:
    """Logged lithology for a drillhole interval."""
    hole_id: str
    from_m: float
    to_m: float
    rock_code: str
    rock_description: str | None = None
    alteration: str | None = None
    mineralisation_description: str | None = None


# ---------------------------------------------------------------------------
# Composite / resource inputs
# ---------------------------------------------------------------------------

@dataclass
class Composite:
    """
    A composited assay interval — drillhole data aggregated to a fixed
    length for resource estimation input.
    """
    hole_id: str
    from_m: float
    to_m: float
    composite_length_m: float
    domain: str                   # geological domain this composite belongs to
    primary_element: str
    composite_grade: float
    grade_unit: str
    secondary_grades: dict[str, float] = field(default_factory=dict)
    weight: float = 1.0           # for weighted compositing


# ---------------------------------------------------------------------------
# Geological domains
# ---------------------------------------------------------------------------

@dataclass
class GeologicalDomain:
    """
    A geological domain used for resource estimation.

    A domain is a volume of rock with statistically similar grade distribution
    and geological continuity — e.g. a specific mineralisation zone,
    oxidation envelope, or structural corridor.
    """
    domain_id: str
    name: str
    primary_element: str
    grade_unit: str

    # Statistical summary (populated by domain_classifier)
    sample_count: int = 0
    mean_grade: float | None = None
    median_grade: float | None = None
    cv: float | None = None              # coefficient of variation — grade variability
    min_grade: float | None = None
    max_grade: float | None = None

    # Geological descriptors
    mineralisation_style: str | None = None   # e.g. "disseminated sulphides", "quartz veins"
    host_lithology: str | None = None
    structural_control: str | None = None
    alteration_type: str | None = None
    oxidation_state: str | None = None       # fresh, transitional, oxide

    # Continuity
    average_drill_spacing_m: float | None = None
    continuity_assessment: str | None = None  # "good", "moderate", "poor"

    notes: str | None = None


# ---------------------------------------------------------------------------
# Resource estimate
# ---------------------------------------------------------------------------

@dataclass
class ResourceCategory:
    """One row of a resource statement — a single classification category."""
    category: str                 # "Measured", "Indicated", "Inferred"
    domain: str | None = None     # which domain, if domain-split resource
    tonnes: float | None = None   # million tonnes (Mt)
    grade: float | None = None    # head grade in grade_unit
    grade_unit: str = ""
    contained_metal: float | None = None
    contained_metal_unit: str = ""
    cut_off_grade: float | None = None
    cut_off_unit: str = ""


@dataclass
class ResourceEstimate:
    """
    The complete resource estimate for a project.

    This is the most critical geological input to the economics engine.
    It defines the ore tonnes and grade available to mine.
    """
    project_id: str
    effective_date: str | None
    classification_system: str | None    # "NI 43-101", "JORC 2012", "PERC"
    qualified_person: str | None
    primary_element: str
    categories: list[ResourceCategory] = field(default_factory=list)

    # Totals (Measured + Indicated — the M&I base for mine planning)
    total_mi_tonnes_mt: float | None = None
    total_mi_grade: float | None = None
    total_mi_contained: float | None = None

    # Inferred (upside but cannot be the basis of FS economics)
    total_inferred_tonnes_mt: float | None = None
    total_inferred_grade: float | None = None

    # Reserve (subset of resource converted through mine planning)
    reserves: list[ResourceCategory] = field(default_factory=list)

    # Cut-off grade used
    cut_off_grade: float | None = None
    cut_off_unit: str = ""
    cut_off_basis: str | None = None     # e.g. "NSR", "breakeven", "gold equiv"

    notes: str | None = None

    def total_by_category(self, category: str) -> tuple[float, float, float]:
        """
        Sum tonnes, grade (tonnage-weighted average), and contained metal for a category.
        Returns (tonnes_mt, avg_grade, contained_metal).
        Grade is weighted by tonnes using the grade field — not derived from metal/tonnes
        which would mix incompatible units (e.g. oz and Mt).
        """
        cats = [c for c in self.categories if c.category.lower() == category.lower()]
        if not cats:
            return 0.0, 0.0, 0.0
        total_t = sum(c.tonnes or 0.0 for c in cats)
        total_metal = sum(c.contained_metal or 0.0 for c in cats)
        # Tonnage-weighted grade using the grade field directly
        graded = [(c.tonnes or 0.0, c.grade or 0.0) for c in cats if c.grade is not None]
        if graded and total_t > 0:
            avg_grade = sum(t * g for t, g in graded) / sum(t for t, _ in graded)
        else:
            avg_grade = 0.0
        return total_t, avg_grade, total_metal


# ---------------------------------------------------------------------------
# Deposit model
# ---------------------------------------------------------------------------

@dataclass
class DepositModelHypothesis:
    """
    The geological interpretation of the deposit — what type it is,
    what controls the mineralisation, and what that means for the mine plan.
    This is interpretive and must be reviewed by a geologist.
    """
    project_id: str
    deposit_type: str | None               # e.g. "porphyry Cu-Au", "orogenic gold"
    mineralisation_controls: list[str] = field(default_factory=list)
    structural_setting: str | None = None
    alteration_zoning: str | None = None
    depth_extent_m: float | None = None
    lateral_extent_m: float | None = None
    dip_direction: str | None = None
    plunge: str | None = None

    # Mining method implications
    likely_mine_type: str | None = None    # "open_pit", "underground", "combined"
    depth_to_economic_grade_m: float | None = None
    stripping_ratio_indication: str | None = None  # "low", "moderate", "high"

    # Analogue deposits
    analogues: list[str] = field(default_factory=list)

    # Confidence in interpretation
    data_basis: str | None = None          # what data this is based on
    key_uncertainties: list[str] = field(default_factory=list)

    generated_by: str = "llm"             # "llm" or "geologist"
    reviewed: bool = False


# ---------------------------------------------------------------------------
# Geological risk
# ---------------------------------------------------------------------------

@dataclass
class GeologicalRisk:
    """
    A single geological risk factor with its economic consequence.
    Feeds into the data_assessments.json and the risk section of the report.
    """
    risk_id: str
    category: str            # "resource", "continuity", "grade_variability",
                             # "mining_method", "metallurgy", "data_quality"
    description: str         # plain English — what the risk is
    economic_direction: str  # "negative", "mixed", "neutral"
    assessment: str          # full paragraph explaining economic implication
    impacts: list[str] = field(default_factory=list)   # which model outputs are affected
    recommended_action: str | None = None
    severity: str = "medium" # "high", "medium", "low"
    source: str | None = None


# ---------------------------------------------------------------------------
# Geological picture — the assembled view of the project
# ---------------------------------------------------------------------------

@dataclass
class GeologicalPicture:
    """
    The complete assembled geological view of a project.

    Built by the geology engine from all available data.
    Passed to the economics engine to build the production schedule.
    Also passed to the LLM to write the geology section of the report.
    """
    project_id: str
    resource_estimate: ResourceEstimate | None = None
    domains: list[GeologicalDomain] = field(default_factory=list)
    deposit_model: DepositModelHypothesis | None = None
    risks: list[GeologicalRisk] = field(default_factory=list)
    data_gaps: list[str] = field(default_factory=list)
    drillhole_count: int | None = None
    total_metres_drilled: float | None = None
    data_coverage_assessment: str | None = None
    continuity_assessment: str | None = None
    study_level_supported: str | None = None  # what study level the data supports
    notes: str | None = None
