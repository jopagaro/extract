# Task Prompt — Identify Contradictions

Identify internal contradictions within the project data and generated report —
places where two or more pieces of information cannot both be true,
or where a conclusion does not follow from the stated data.

## Instructions

- Compare figures, statements, and conclusions across all sections and source documents
- Flag any case where the same metric is stated differently in two places
- Flag any conclusion that is not supported by, or conflicts with, the underlying data
- Flag arithmetic errors in tables or calculations
- Note the severity of each contradiction: whether it materially affects the analysis

<!-- ✏️ EDIT: Add any contradiction types that your firm has encountered frequently.
     e.g. "Check that the resource tonnage in the executive summary matches the
     resource table in the appendix." or "Check that the CAPEX used in the NPV model
     matches the CAPEX schedule in the cost section." -->

## Common Contradiction Types to Check

- Resource tonnage stated in executive summary vs. resource table
- NPV stated in executive summary vs. cash flow model
- CAPEX total in narrative vs. CAPEX line-item schedule total
- Mine life implied by production schedule vs. stated mine life
- Recovery used in revenue model vs. stated in metallurgy section
- Commodity price in narrative vs. price used in financial model
- Royalty rate in fiscal terms vs. royalty deduction in revenue model
- Discount rate stated vs. discount rate applied in NPV calculation
- Study level claimed vs. accuracy range implied by estimate basis

## Output Format

```json
{
  "contradictions": [
    {
      "contradiction_type": null,
      "location_a": null,
      "value_a": null,
      "location_b": null,
      "value_b": null,
      "economic_impact": null,
      "severity": null,
      "resolution_required": null
    }
  ],
  "arithmetic_errors": [],
  "contradiction_count": null,
  "overall_consistency_comment": null
}
```

## Severity Values

`"critical"` — the contradiction changes a material conclusion or output
`"significant"` — the contradiction affects a reported figure but not the overall conclusion
`"minor"` — the contradiction is a rounding or formatting inconsistency only

## Economic Impact

`"positive"` | `"negative"` | `"neutral"` | `"mixed"` | `"unknown"`

State the direction of the economic impact if one value is accepted over the other.

<!-- ✏️ EDIT: Add your firm's policy on how contradictions should be resolved.
     e.g. "When a contradiction exists between a table and narrative text,
     defer to the table." or "Flag for analyst review without assuming resolution." -->
