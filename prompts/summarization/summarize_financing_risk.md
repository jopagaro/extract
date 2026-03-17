# Task Prompt — Summarize Financing Risk

Write a structured analysis of the financing risk for this mining project.

Financing risk encompasses: the probability the project can secure the capital
required to build, the terms under which that capital might be available, and
the economic impact of those terms on the project returns.

## Instructions

- Assess the financing requirement against the project's economic profile
- Identify financing structures mentioned or implied by the project data
- Note any off-take agreements, streaming deals, or royalty financings referenced
- Flag any capital requirement that appears difficult to finance given project stage and scale
- Do not speculate about specific lenders or investors

<!-- ✏️ EDIT: Add context specific to the financing environments you cover.
     e.g. "Note whether the project is eligible for export credit agency (ECA) financing."
     or "Flag if the CAPEX exceeds the typical threshold for junior developer balance sheets
     in this commodity sector." Add your firm's capital cost thresholds here. -->

## Output Format

```json
{
  "financing_overview": null,
  "capex_requirement": null,
  "equity_requirement_estimate": null,
  "debt_capacity_comment": null,
  "financing_structures_identified": [],
  "offtake_agreements": [],
  "streaming_or_royalty_financing": [],
  "sponsor_financial_position_comment": null,
  "key_financing_risks": [],
  "financing_timeline_comment": null,
  "word_count": null
}
```

## Writing Standards

<!-- ✏️ EDIT: Replace with your firm's financing section conventions -->

- **Financing overview**: State the total CAPEX requirement and what proportion is likely debt vs equity
- **Debt capacity comment**: Assess whether the project metrics (NPV, cash flows, DSCR) support project finance
- **Sponsor financial position**: What does the project data say about the developer's ability to fund their equity share?
- **Key financing risks**: Specific scenarios where financing could fail or be delayed materially

## Tone

Objective. Financing risk is often understated in company documents.
The summary should state clearly if the financing path is unclear or high-risk.
