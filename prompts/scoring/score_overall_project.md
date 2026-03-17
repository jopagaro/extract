# Task Prompt — Score Overall Project

Synthesize all individual domain assessments into an overall project evaluation.

This is the final analytical step. You receive the geology, economics, financing,
and permitting assessments and produce a single integrated view of the project's
strengths, weaknesses, and development readiness.

## Input

You will receive:
- Geology score assessment
- Economics score assessment
- Financing score assessment
- Permitting score assessment
- Risk summary

## Instructions

- Synthesize across all domains — do not simply repeat each domain assessment
- Identify the single most important issue for the project's advancement
- Identify the strongest element of the project
- State clearly what would need to change for this project to advance to the next study level
- Do not provide an investment recommendation

<!-- ✏️ EDIT: Add any overall project evaluation criteria specific to your firm.
     e.g. "Always state whether the project meets the firm's minimum return threshold
     of [X%] IRR at [Y]% discount rate." or "Always reference the project against
     the firm's sector benchmark for CAPEX intensity ($/oz, $/lb, $/t)."
     Add your firm's development readiness checklist here. -->

## Output Format

```json
{
  "overall_summary": null,
  "primary_strength": null,
  "primary_risk": null,
  "development_readiness_comment": null,
  "next_steps_required": [],
  "domain_summary": {
    "geology": null,
    "economics": null,
    "financing": null,
    "permitting": null
  },
  "data_gaps_blocking_advancement": [],
  "word_count": null
}
```

## Writing Standards

<!-- ✏️ EDIT: Replace with your firm's overall evaluation conventions -->

**Overall summary**: 2-3 sentences synthesizing the project's current state across all domains.

**Primary strength**: The single most positive factor for this project's advancement.

**Primary risk**: The single most material risk to project delivery or economics.

**Development readiness**: Explicitly state what study level the project is at and
what is required to advance to the next level. Be specific about what data, studies,
or approvals are needed.

**Next steps required**: A numbered list of the concrete actions required to advance
the project, in priority order.

## Tone

Balanced and honest. The overall evaluation must not tilt positive or negative
based on anything other than the evidence. State confidence clearly.
Do not use investment language under any circumstances.
