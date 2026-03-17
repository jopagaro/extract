# Task Prompt — Extract Management Claims and Forward-Looking Statements

Extract claims made by management or the study authors that are forward-looking,
promotional, or not directly supported by the underlying technical data.

## Instructions

- Extract every statement that is an opinion, expectation, or forecast rather than a measured fact
- Flag any language that is promotional or investment-oriented
- Note the section and page number for each claim
- Do not evaluate whether the claims are true — only extract and categorise them
- Use null for any field not found

<!-- ✏️ EDIT: Add specific language patterns your compliance team flags as problematic
     e.g. "world-class", "tier-1", "company-maker", "transformational asset",
     "re-rate catalyst", "undervalued". Add your firm's blacklist phrases here. -->

## Output Format

```json
{
  "claims": [
    {
      "claim_text": null,
      "category": null,
      "basis_stated": null,
      "verifiable_in_data": null,
      "compliance_flag": null,
      "section": null,
      "source_page": null
    }
  ],
  "promotional_language_detected": [],
  "investment_language_detected": [],
  "unsupported_assertions": [],
  "notes": null
}
```

## Category Values

- `"production_target"` — forecast production volumes or grades
- `"cost_target"` — forecast CAPEX or OPEX below study estimates
- `"timeline"` — forecast construction start, first production, or milestones
- `"resource_growth"` — claims about potential resource upside
- `"strategic"` — statements about company strategy or project significance
- `"valuation"` — statements that imply project or company value
- `"other"` — anything not covered above

## Compliance Flags

Set `compliance_flag` to `true` if the claim:
- Contains language that implies investment attractiveness
- Predicts share price, company value, or return to shareholders
- Describes the project as "world class", "tier-1", "transformational", or similar superlatives
- Makes production or cost promises beyond the study scope

<!-- ✏️ EDIT: Replace or extend the compliance flag criteria above with your firm's
     specific standards — e.g. ASX continuous disclosure rules, NI 51-102,
     SEC Regulation S-K, or internal house style rules -->

## Important

This extraction feeds the critic and compliance review steps.
Extract every qualifying statement — err on the side of inclusion.
