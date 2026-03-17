"""
Deposit model hypothesizer.

Builds a DepositModelHypothesis from available geological data.

Without a 3D model or a geologist's interpretation, the hypothesis is
assembled from evidence in the drillhole data and resource estimate:
  - Lithology and alteration patterns
  - Grade-depth relationships
  - Structural orientation (from collar azimuth/dip distributions)
  - Analogues by deposit type

This module produces an LLM-reviewable hypothesis — it is deliberately
interpretive and must always be reviewed by a geologist before use.
All generated hypotheses carry generated_by="llm" and reviewed=False.

The LLM integration path:
  deposit_model_hypothesizer.hypothesize_from_data()
      → assembles evidence summary
      → passes to llm.dual_runner for interpretation
      → returns DepositModelHypothesis with reviewed=False
"""

from __future__ import annotations

from engine.core.logging import get_logger
from engine.geology.models import (
    Collar,
    DepositModelHypothesis,
    GeologicalDomain,
    GeologicalPicture,
    LithologyInterval,
    ResourceEstimate,
)

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Known deposit type patterns for evidence-based matching
# ---------------------------------------------------------------------------

_DEPOSIT_PATTERNS: list[dict] = [
    {
        "deposit_type": "orogenic gold",
        "rock_codes": {"qvn", "bxs", "sst", "phyl", "qtz"},
        "alteration_keys": {"silicification", "carbonate", "sulphidation", "sericitisation"},
        "structural_keywords": {"shear", "fault", "fold", "vein"},
        "typical_mine_type": "underground",
    },
    {
        "deposit_type": "porphyry Cu-Au",
        "rock_codes": {"pphy", "qmphy", "dio", "grnd", "dior"},
        "alteration_keys": {"potassic", "phyllic", "propylitic", "argillic"},
        "structural_keywords": {"porphyry", "intrusion", "breccia", "disseminated"},
        "typical_mine_type": "open_pit",
    },
    {
        "deposit_type": "epithermal Au-Ag",
        "rock_codes": {"rhyo", "and", "tuff", "brx", "vein"},
        "alteration_keys": {"adularia", "illite", "silicification", "alunite", "kaolinite"},
        "structural_keywords": {"vein", "stockwork", "breccia", "low sulphidation"},
        "typical_mine_type": "underground",
    },
    {
        "deposit_type": "IOCG (iron oxide copper-gold)",
        "rock_codes": {"mag", "hem", "bxs", "grnd", "biot"},
        "alteration_keys": {"magnetite", "hematite", "sodic", "calcic", "chlorite"},
        "structural_keywords": {"breccia", "fault", "iron oxide"},
        "typical_mine_type": "open_pit",
    },
    {
        "deposit_type": "sediment-hosted gold (Carlin-style)",
        "rock_codes": {"lst", "dolo", "slt", "sst", "carb"},
        "alteration_keys": {"decarbonatization", "jasperoid", "silicification", "argillic"},
        "structural_keywords": {"fold", "thrust", "reactive", "sediment"},
        "typical_mine_type": "open_pit",
    },
]


def hypothesize_from_data(
    resource: ResourceEstimate | None,
    collars: list[Collar] | None = None,
    lithology: list[LithologyInterval] | None = None,
    domains: list[GeologicalDomain] | None = None,
    notes: str | None = None,
) -> DepositModelHypothesis:
    """
    Build a DepositModelHypothesis from available drillhole and resource data.

    This is a rule-based first pass. The result should be reviewed by the LLM
    and then by a geologist before being used in reporting.

    Returns a DepositModelHypothesis with generated_by="llm" and reviewed=False.
    """
    project_id = resource.project_id if resource else "unknown"

    # --- Collect evidence ---
    evidence = _collect_evidence(resource, collars, lithology, domains)
    deposit_type, mine_type = _match_deposit_type(evidence)
    uncertainties = _identify_uncertainties(resource, collars, lithology)

    # --- Depth and extent ---
    depth_extent = _estimate_depth_extent(collars)
    dip_direction = _estimate_dip_direction(collars)

    # --- Stripping ratio indication ---
    stripping_hint = _estimate_stripping_indication(mine_type, depth_extent)

    hypothesis = DepositModelHypothesis(
        project_id=project_id,
        deposit_type=deposit_type,
        mineralisation_controls=evidence.get("structural_evidence", []),
        structural_setting=evidence.get("structural_setting"),
        alteration_zoning=", ".join(evidence.get("alteration_types", [])) or None,
        depth_extent_m=depth_extent,
        dip_direction=dip_direction,
        likely_mine_type=mine_type,
        stripping_ratio_indication=stripping_hint,
        data_basis=_summarise_data_basis(resource, collars, lithology),
        key_uncertainties=uncertainties,
        analogues=[],
        generated_by="llm",
        reviewed=False,
    )

    log.info(
        "Deposit model hypothesis generated | type=%s mine_type=%s uncertainties=%d",
        deposit_type, mine_type, len(uncertainties),
    )

    if notes:
        # Can't set notes on the dataclass directly without it being in the model;
        # if the model is extended, this is the hook
        pass

    return hypothesis


def hypothesize_from_picture(picture: GeologicalPicture) -> DepositModelHypothesis:
    """
    Convenience wrapper: build a hypothesis from an assembled GeologicalPicture.
    """
    return hypothesize_from_data(
        resource=picture.resource_estimate,
        domains=picture.domains,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _collect_evidence(
    resource: ResourceEstimate | None,
    collars: list[Collar] | None,
    lithology: list[LithologyInterval] | None,
    domains: list[GeologicalDomain] | None,
) -> dict:
    """Collect evidence strings from all available data."""
    evidence: dict = {
        "rock_codes": set(),
        "alteration_types": [],
        "mineralisation_styles": [],
        "structural_evidence": [],
        "primary_element": resource.primary_element.lower() if resource else "unknown",
        "structural_setting": None,
    }

    if lithology:
        for lith in lithology:
            if lith.rock_code:
                evidence["rock_codes"].add(lith.rock_code.lower()[:4])
            if lith.alteration:
                alt = lith.alteration.lower()
                if alt not in evidence["alteration_types"]:
                    evidence["alteration_types"].append(alt)
            if lith.mineralisation_description:
                desc = lith.mineralisation_description.lower()
                evidence["mineralisation_styles"].append(desc)
                for kw in ("vein", "shear", "fault", "breccia", "disseminated", "stockwork"):
                    if kw in desc and kw not in evidence["structural_evidence"]:
                        evidence["structural_evidence"].append(kw)

    if domains:
        for domain in domains:
            if domain.mineralisation_style and domain.mineralisation_style not in evidence["mineralisation_styles"]:
                evidence["mineralisation_styles"].append(domain.mineralisation_style)
            if domain.structural_control and domain.structural_control not in evidence["structural_evidence"]:
                evidence["structural_evidence"].append(domain.structural_control)
            if domain.alteration_type and domain.alteration_type not in evidence["alteration_types"]:
                evidence["alteration_types"].append(domain.alteration_type)

    return evidence


def _match_deposit_type(evidence: dict) -> tuple[str, str]:
    """Score deposit patterns against evidence. Return best match."""
    primary = evidence.get("primary_element", "")
    rock_codes = evidence.get("rock_codes", set())
    alteration_types = set(a.lower() for a in evidence.get("alteration_types", []))
    structural = set(s.lower() for s in evidence.get("structural_evidence", []))

    best_score = 0
    best_type = "undetermined"
    best_mine = "open_pit"

    for pattern in _DEPOSIT_PATTERNS:
        score = 0
        score += len(rock_codes & pattern["rock_codes"]) * 2
        score += len(alteration_types & pattern["alteration_keys"]) * 3
        for kw in pattern["structural_keywords"]:
            if any(kw in s for s in structural):
                score += 1

        if score > best_score:
            best_score = score
            best_type = pattern["deposit_type"]
            best_mine = pattern["typical_mine_type"]

    # If no evidence matches, fall back to primary element hint
    if best_score == 0:
        if primary in ("au", "gold"):
            best_type = "gold deposit (type undetermined)"
        elif primary in ("cu", "copper"):
            best_type = "copper deposit (type undetermined)"
            best_mine = "open_pit"
        elif primary in ("li", "lithium"):
            best_type = "lithium deposit (type undetermined)"
            best_mine = "open_pit"

    return best_type, best_mine


def _identify_uncertainties(
    resource: ResourceEstimate | None,
    collars: list[Collar] | None,
    lithology: list[LithologyInterval] | None,
) -> list[str]:
    uncertainties = []
    if not resource:
        uncertainties.append("No resource estimate available — deposit type entirely inferential")
    if not collars or len(collars) < 5:
        uncertainties.append("Fewer than 5 drillholes — insufficient data to constrain deposit geometry")
    if not lithology:
        uncertainties.append("No lithology logging available — mineralisation controls cannot be assessed")
    if resource and resource.classification_system is None:
        uncertainties.append("Resource classification system not recorded")
    uncertainties.append(
        "Deposit model is an automated hypothesis — must be reviewed by a qualified geologist"
    )
    return uncertainties


def _estimate_depth_extent(collars: list[Collar] | None) -> float | None:
    if not collars:
        return None
    depths = [c.total_depth_m for c in collars if c.total_depth_m is not None]
    if not depths:
        return None
    return round(max(depths), 0)


def _estimate_dip_direction(collars: list[Collar] | None) -> str | None:
    if not collars:
        return None
    dips = [c.dip for c in collars if c.dip is not None]
    if not dips:
        return None
    avg_dip = sum(dips) / len(dips)
    if avg_dip < -70:
        return "subvertical"
    elif avg_dip < -45:
        return "steeply dipping"
    else:
        return "moderately dipping"


def _estimate_stripping_indication(mine_type: str, depth_extent_m: float | None) -> str | None:
    if mine_type != "open_pit":
        return None
    if depth_extent_m is None:
        return "unknown"
    if depth_extent_m < 100:
        return "low"
    elif depth_extent_m < 300:
        return "moderate"
    else:
        return "high"


def _summarise_data_basis(
    resource: ResourceEstimate | None,
    collars: list[Collar] | None,
    lithology: list[LithologyInterval] | None,
) -> str:
    parts = []
    if resource:
        parts.append(f"{resource.classification_system or 'JORC/NI 43-101'} resource estimate")
    if collars:
        parts.append(f"{len(collars)} drillhole collar(s)")
    if lithology:
        parts.append(f"{len(lithology)} lithology interval(s)")
    if not parts:
        return "No data basis — hypothesis is entirely speculative"
    return "; ".join(parts)
