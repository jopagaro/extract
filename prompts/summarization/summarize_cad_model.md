# Task Prompt — Summarize CAD Model

Write a concise technical description of the mine design and 3D models
associated with this mining project.

The input will be structured CAD semantic data — layer names, object types,
design parameters, and bounding geometry extracted from the model files.

## Instructions

- Describe the mine design in plain language a non-CAD-specialist can understand
- Highlight the key design parameters that affect the economic model
- Note any design elements that appear incomplete or preliminary
- Do not invent design specifications not present in the model data

<!-- ✏️ EDIT: Add the mine design parameters most relevant to the project types
     your firm typically covers. e.g. for open pit projects: emphasize slope angles
     and strip ratios. For underground: stope dimensions and dilution assumptions.
     For heap leach: pad footprint and liner specifications. -->

## Output Format

```json
{
  "design_overview": null,
  "mine_type_confirmed": null,
  "key_design_parameters": null,
  "pit_or_underground_description": null,
  "infrastructure_summary": null,
  "design_completeness_comment": null,
  "design_assumptions_flagged": [],
  "word_count": null
}
```

## Writing Standards

<!-- ✏️ EDIT: Replace with your firm's CAD section conventions -->

- **Design overview**: 1-2 sentences on the overall mine design — type, scale, and stage of design development
- **Key design parameters**: The 3-5 numbers from the model that most affect the economics (pit depth, ramp gradient, stope width, etc.)
- **Infrastructure summary**: Describe any surface infrastructure visible in the model — plant, tailings, roads, power
- **Design completeness**: Is this a conceptual layout, pre-feasibility design, or detailed engineering? What is missing?

## Tone

Technical and precise. Mine design sections inform the CAPEX and OPEX estimates.
Note any design parameter that appears to be assumed rather than engineered.
