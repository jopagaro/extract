"""
OpenAI tool schemas for structured extraction.

Each tool definition forces the LLM to return data in an exact schema
rather than free-form JSON. This eliminates json_mode unreliability and
removes the need for retry logic on malformed extraction outputs.

Usage: pass the tool to call_openai_with_tools() with tool_choice forced
to that specific function so the model always calls it.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _nullable_str(description: str) -> dict:
    return {"anyOf": [{"type": "string"}, {"type": "null"}], "description": description}

def _nullable_num(description: str) -> dict:
    return {"anyOf": [{"type": "number"}, {"type": "null"}], "description": description}

def _nullable_bool(description: str) -> dict:
    return {"anyOf": [{"type": "boolean"}, {"type": "null"}], "description": description}

def _nullable_int(description: str) -> dict:
    return {"anyOf": [{"type": "integer"}, {"type": "null"}], "description": description}


# ---------------------------------------------------------------------------
# Project Facts
# ---------------------------------------------------------------------------

PROJECT_FACTS_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "record_project_facts",
        "description": (
            "Record the core identifying facts extracted from a mining project document. "
            "Use null for every field not explicitly stated in the document. "
            "Do not infer, calculate, or assume values."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "project_name": _nullable_str("Full project name as stated in the document"),
                "operator": _nullable_str("Company operating or developing the project"),
                "project_location": {
                    "type": "object",
                    "properties": {
                        "country": _nullable_str("Country where the project is located"),
                        "region_or_state": _nullable_str("Province, state, or region"),
                        "nearest_town": _nullable_str("Nearest named settlement"),
                        "coordinates": _nullable_str("Lat/lon or UTM coordinates as stated"),
                    },
                },
                "commodity_primary": _nullable_str("Main economic mineral (e.g. gold, copper, lithium)"),
                "commodities_secondary": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "By-products or co-products with economic value",
                },
                "deposit_type": _nullable_str("Geological classification (e.g. porphyry copper, orogenic gold)"),
                "mine_type": _nullable_str("open pit, underground, heap leach, in-situ, placer, or combination"),
                "study_level": _nullable_str("scoping, PEA, PFS, FS, or historical"),
                "study_date": _nullable_str("Date the study was published or completed"),
                "study_author": _nullable_str("Consulting firm or individual who authored the study"),
                "project_status": _nullable_str("e.g. exploration, development, construction, production, care and maintenance"),
                "land_package": {
                    "type": "object",
                    "properties": {
                        "area_ha": _nullable_num("Land package area in hectares"),
                        "tenure_type": _nullable_str("e.g. mining licence, mineral claim, concession"),
                        "ownership_percent": _nullable_num("Operator ownership percentage of the project"),
                    },
                },
                "sources": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "field": {"type": "string", "description": "Which field this source supports"},
                            "page": _nullable_int("Page number in the source document"),
                            "section": _nullable_str("Section heading in the source document"),
                        },
                        "required": ["field"],
                    },
                    "description": "Source locations for extracted values",
                },
            },
            "required": [],
        },
    },
}

_TOOL_CHOICE_PROJECT_FACTS: dict = {
    "type": "function",
    "function": {"name": "record_project_facts"},
}


# ---------------------------------------------------------------------------
# Economic Assumptions
# ---------------------------------------------------------------------------

ECONOMIC_ASSUMPTIONS_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "record_economic_assumptions",
        "description": (
            "Record CAPEX, OPEX, and economic assumptions extracted from a mining study. "
            "Use null for every field not explicitly stated. "
            "If a figure appears with conflicting values, extract all instances and flag in sources."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "capex": {
                    "type": "object",
                    "properties": {
                        "initial_capex": _nullable_num("Initial capital cost as stated"),
                        "initial_capex_unit": _nullable_str("Unit of initial capex (e.g. M USD, B CAD)"),
                        "sustaining_capex_total": _nullable_num("Total sustaining capital over mine life"),
                        "sustaining_capex_per_year": _nullable_num("Average annual sustaining capex"),
                        "sustaining_capex_unit": _nullable_str("Unit of sustaining capex"),
                        "closure_cost": _nullable_num("Reclamation and closure cost"),
                        "closure_cost_unit": _nullable_str("Unit of closure cost"),
                        "contingency_percent": _nullable_num("Contingency as a percentage of total capex"),
                        "accuracy_range": _nullable_str("Stated accuracy e.g. ±25% — indicates study level rigour"),
                        "effective_date": _nullable_str("Date costs were estimated (Q1 2023, etc.)"),
                        "capex_breakdown": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "item": {"type": "string"},
                                    "value": _nullable_num("Cost value"),
                                    "unit": _nullable_str("Cost unit"),
                                },
                                "required": ["item"],
                            },
                            "description": "Line-item capex breakdown if provided",
                        },
                    },
                },
                "opex": {
                    "type": "object",
                    "properties": {
                        "total_cash_cost": _nullable_num("Total cash cost per unit produced"),
                        "total_cash_cost_unit": _nullable_str("Unit (e.g. USD/oz, USD/lb)"),
                        "aisc": _nullable_num("All-In Sustaining Cost if stated"),
                        "aisc_unit": _nullable_str("AISC unit"),
                        "mining_cost": _nullable_num("Mining cost component"),
                        "processing_cost": _nullable_num("Processing/milling cost component"),
                        "ganda_cost": _nullable_num("General and administrative cost"),
                        "cost_unit": _nullable_str("Unit for mining/processing/G&A costs"),
                        "basis": _nullable_str("Per tonne ore, per tonne total material, or per oz produced"),
                    },
                },
                "economics": {
                    "type": "object",
                    "properties": {
                        "commodity_price_assumptions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "commodity": {"type": "string"},
                                    "price": _nullable_num("Price value"),
                                    "unit": _nullable_str("e.g. USD/oz, USD/lb"),
                                    "basis": _nullable_str("e.g. spot, long-term consensus, analyst forecast"),
                                },
                                "required": ["commodity"],
                            },
                        },
                        "exchange_rate_assumptions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "pair": {"type": "string", "description": "e.g. USD:CAD"},
                                    "rate": _nullable_num("Exchange rate value"),
                                },
                                "required": ["pair"],
                            },
                        },
                        "discount_rate_percent": _nullable_num("Discount rate used in DCF (e.g. 5, 8, 10)"),
                        "npv": _nullable_num("Net present value as stated"),
                        "npv_unit": _nullable_str("NPV unit (e.g. M USD)"),
                        "irr_percent": _nullable_num("Internal rate of return as stated"),
                        "payback_years": _nullable_num("Undiscounted payback period in years"),
                        "after_tax": _nullable_bool("Whether NPV and IRR are stated on an after-tax basis"),
                    },
                },
                "royalties": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "description": "e.g. NSR, NPI, GR, stream"},
                            "rate": _nullable_num("Royalty rate or stream percentage"),
                            "basis": _nullable_str("What the royalty is applied to"),
                            "payable_to": _nullable_str("Royalty holder"),
                        },
                        "required": ["type"],
                    },
                },
                "taxes": {
                    "type": "object",
                    "properties": {
                        "corporate_tax_rate_percent": _nullable_num("Stated corporate income tax rate"),
                        "jurisdiction": _nullable_str("Tax jurisdiction"),
                        "notes": _nullable_str("Any special tax treatment or mining taxes noted"),
                    },
                },
                "sources": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "field": {"type": "string"},
                            "page": _nullable_int("Page number"),
                            "section": _nullable_str("Section heading"),
                            "note": _nullable_str("Flag discrepancies or conflicting values here"),
                        },
                        "required": ["field"],
                    },
                },
            },
            "required": [],
        },
    },
}

_TOOL_CHOICE_ECONOMIC_ASSUMPTIONS: dict = {
    "type": "function",
    "function": {"name": "record_economic_assumptions"},
}


# ---------------------------------------------------------------------------
# Mine Plan Inputs
# ---------------------------------------------------------------------------

MINE_PLAN_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "record_mine_plan_inputs",
        "description": (
            "Record mine plan and production schedule parameters from a mining study. "
            "Use null for fields not found. If only an average annual production figure is given "
            "(not a full schedule), record it as a single row with year set to 'average'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "mine_type": _nullable_str("open pit, underground, heap leach, in-situ, placer, or combination"),
                "mining_method": _nullable_str("e.g. conventional truck-and-shovel, longhole stoping, sublevel caving"),
                "mine_life_years": _nullable_num("Total mine life in years"),
                "throughput": {
                    "type": "object",
                    "properties": {
                        "value": _nullable_num("Throughput rate value"),
                        "unit": _nullable_str("e.g. tpd, Mtpa"),
                        "basis": _nullable_str("ore processed, ore mined, or total material"),
                    },
                },
                "strip_ratio": {
                    "type": "object",
                    "properties": {
                        "value": _nullable_num("Strip ratio value"),
                        "unit": _nullable_str("waste:ore by tonnes, or total material:ore — preserve as stated"),
                    },
                },
                "production_schedule": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "year": {"anyOf": [{"type": "integer"}, {"type": "string"}, {"type": "null"}], "description": "Mine year or 'average'"},
                            "ore_tonnes": _nullable_num("Ore tonnes for this year"),
                            "ore_grade_primary": _nullable_num("Primary commodity grade"),
                            "ore_grade_unit": _nullable_str("Grade unit (e.g. g/t, %, lb/t)"),
                            "waste_tonnes": _nullable_num("Waste tonnes for this year"),
                            "contained_metal": _nullable_num("Contained metal for this year"),
                            "contained_metal_unit": _nullable_str("Unit (e.g. koz, Mlb)"),
                        },
                    },
                    "description": "Year-by-year production schedule if available",
                },
                "mining_rate": {
                    "type": "object",
                    "properties": {
                        "ore_per_day": _nullable_num("Ore mining rate per day"),
                        "total_material_per_day": _nullable_num("Total material (ore + waste) per day"),
                        "unit": _nullable_str("Unit (e.g. tpd, bcmd)"),
                    },
                },
                "equipment": {
                    "type": "object",
                    "properties": {
                        "primary_fleet": _nullable_str("Primary mining equipment type"),
                        "fleet_size": _nullable_int("Number of primary units"),
                    },
                },
                "preproduction_period_months": _nullable_num("Time from construction start to first ore in months"),
                "ramp_up_period_months": _nullable_num("Time from first ore to full production rate in months"),
                "sources": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "field": {"type": "string"},
                            "page": _nullable_int("Page number"),
                            "section": _nullable_str("Section heading"),
                        },
                        "required": ["field"],
                    },
                },
            },
            "required": [],
        },
    },
}

_TOOL_CHOICE_MINE_PLAN: dict = {
    "type": "function",
    "function": {"name": "record_mine_plan_inputs"},
}


# ---------------------------------------------------------------------------
# Public tool_choice constants (import alongside the tool dicts)
# ---------------------------------------------------------------------------

TOOL_CHOICE_PROJECT_FACTS = _TOOL_CHOICE_PROJECT_FACTS
TOOL_CHOICE_ECONOMIC_ASSUMPTIONS = _TOOL_CHOICE_ECONOMIC_ASSUMPTIONS
TOOL_CHOICE_MINE_PLAN = _TOOL_CHOICE_MINE_PLAN
