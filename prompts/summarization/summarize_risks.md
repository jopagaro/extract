# Task Prompt — Summarize Risks

Write a structured risk summary for this mining project, drawing on all available
project data: geological, technical, economic, permitting, and social.

## Instructions

- Identify and describe all material risks to project delivery and economics
- Classify each risk by category and potential economic impact direction
- Be specific — general statements like "commodity price risk exists" are not useful
- Do not rate or score risks numerically — describe them in plain language
- Note where mitigation measures are identified in the project data

<!-- ✏️ EDIT: Add any risk categories specific to your firm's coverage universe
     e.g. country-specific political risk (coups, nationalisation, mining code changes),
     specific commodity risks (lithium hydroxide conversion risk, gold streaming terms),
     or climate/water risk categories relevant to your typical jurisdictions. -->

## Output Format

```json
{
  "risk_summary_narrative": null,
  "risks": [
    {
      "risk_name": null,
      "category": null,
      "description": null,
      "economic_direction": null,
      "mitigation_stated": null,
      "data_gap": null
    }
  ],
  "top_three_risks": [],
  "data_gaps_summary": null,
  "word_count": null
}
```

## Risk Categories

<!-- ✏️ EDIT: Add, remove, or rename categories to match your firm's risk taxonomy -->

- `"geological"` — resource estimation uncertainty, continuity, grade variability
- `"geotechnical"` — pit slope stability, underground ground conditions
- `"metallurgical"` — recovery variability, processing plant performance
- `"capex"` — construction cost overruns, equipment availability
- `"opex"` — operating cost escalation, labour, energy, reagents
- `"commodity_price"` — primary and by-product price assumptions
- `"currency"` — exchange rate exposure
- `"permitting"` — regulatory approval delays, conditions
- `"social"` — community opposition, resettlement, social licence
- `"political"` — sovereign risk, mining code, fiscal regime changes
- `"water"` — water availability, discharge, acid rock drainage
- `"infrastructure"` — power, roads, logistics, grid connection
- `"financing"` — project funding, debt terms, equity dilution
- `"technical"` — engineering design, technology selection
- `"environmental"` — closure liability, contamination, rehabilitation

## Economic Direction

Use one of: `"positive"`, `"negative"`, `"neutral"`, `"mixed"`

## Tone

Direct and honest. Name the specific risk clearly.
Do not soften risks with language like "manageable" unless the document explicitly
provides a management plan that supports that conclusion.
