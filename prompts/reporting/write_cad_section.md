# Task Prompt — Write CAD and Mine Design Section

Write the mine design and infrastructure section of the technical report,
based on the 3D model analysis and design parameter extraction.

## Input

You will receive:
- CAD semantic summary (layers, object types, design parameters)
- Mine type and design stage
- Key design parameters (slope angles, bench heights, access, ramp geometry)
- Infrastructure components identified in the model

## Instructions

- Describe the mine design in plain language complementing the 3D model data
- State which design elements are confirmed vs. assumed at this study level
- Note any design features that materially affect the capital or operating cost estimate
- Do not overstate the completeness of a conceptual or pre-feasibility layout

<!-- ✏️ EDIT: Add any mine design parameters mandatory for your study types.
     e.g. "Always state inter-ramp slope angles and berm widths for open pit designs."
     or "Always describe the decline portal location and gradient for underground."
     Add figure/drawing reference conventions if your reports include CAD screenshots. -->

## Output Format

```json
{
  "section_title": "Mine Design and Infrastructure",
  "subsections": [
    {
      "heading": null,
      "level": null,
      "text": null
    }
  ],
  "design_parameters_table": [
    {"parameter": null, "value": null, "unit": null, "basis": null}
  ],
  "word_count": null
}
```

## Sub-section Guidelines

<!-- ✏️ EDIT: Replace with your firm's mine design section standards -->

**Mine Type and Design Stage**: State whether open pit, underground, or combined.
State the design stage — conceptual, pre-feasibility, feasibility.

**Pit / Underground Design** (as applicable): Describe the key geometric parameters.
For open pit: overall slope angles, inter-ramp angles, bench heights, berm widths,
pit dimensions, and strip ratio. For underground: access type, stoping method,
level spacing, dilution assumption.

**Production Infrastructure**: Describe the process plant location, tailings facility,
waste dumps, and any other major surface infrastructure identified in the model.

**Access and Logistics**: Describe site access — road, port, rail, power source.

**Design Limitations**: Note what has not been designed at this stage and the
impact on cost estimate accuracy.

## Tone

Technical. Describe the design as it is, not as it might eventually be.
Flag any design assumption that is load-bearing for the CAPEX estimate.
