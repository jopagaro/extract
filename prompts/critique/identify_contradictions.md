# Task Prompt — Identify Contradictions & Consistency Issues

You are a senior mining analyst performing an independent consistency review of a
technical report. Your job is to find every place where two or more pieces of
information within this document cannot both be true — or where a stated conclusion
is not supported by the underlying data.

This is an adversarial review. Assume the report may contain errors introduced by
copy-paste, rounding, section-by-section drafting, or model assumptions that were
changed mid-study but not updated everywhere.

## What to Check

### Numeric Contradictions
- Resource tonnage stated in the executive summary vs. the resource table
- Contained metal in the summary vs. tonnage × grade (arithmetic consistency)
- NPV or IRR stated in text vs. the value that emerges from the cash flow model
- CAPEX total in the narrative vs. the sum of line items in the cost schedule
- Mine life implied by the production schedule (total ore / annual throughput)
  vs. the stated mine life
- Recovery rate used in the revenue model vs. stated in the metallurgy section
- Commodity price used in financial projections vs. price stated in assumptions table
- Discount rate stated in the text vs. discount rate applied in the NPV calculation
- NSR/royalty rate in the fiscal terms section vs. deduction in the revenue model
- Strip ratio used in the mining cost vs. the pit design strip ratio in geology

### Logical / Narrative Contradictions
- Study classification claimed (e.g. PFS) vs. accuracy range or classification basis
  described elsewhere in the document
- A conclusion that a project is "economic" when the NPV is negative at the base case
- Statements about resource confidence that are inconsistent with the resource
  classification table (e.g. calling a deposit "well-defined" when most resources
  are Inferred)
- Environmental or permitting status described as "advanced" when the executive
  summary says "pre-application"

### Temporal Contradictions
- Dates that are out of sequence (e.g. construction start before permitting approval)
- Historical price references mixed with forward price assumptions without disclosure
- Resource estimates from different dates combined without reconciliation disclosure

### Arithmetic Errors
- Contained metal = tonnage × grade: check gold (Mt × g/t ÷ 31.1035 = Moz),
  copper (Mt × % × 10 = kt), silver (Mt × g/t ÷ 31.1035 = Moz)
- Total CAPEX ≠ sum of CAPEX line items
- Total OpEx per tonne ≠ sum of cost components
- Annual revenue ≠ production × price × recovery
- Payback period inconsistent with cumulative cash flow turning positive

## Instructions

1. Review all numeric figures, dates, classifications, and conclusions systematically
2. Flag every case where two stated values for the same metric differ by more than
   normal rounding (>2% discrepancy is significant; >10% is critical)
3. Flag every conclusion that is not logically supported by the data as presented
4. For each contradiction: identify both source locations, quote both values, assess
   severity, and estimate the direction of economic impact
5. If you identify an arithmetic error, show the correct calculation
6. Do NOT flag items as contradictions if the discrepancy is clearly attributable
   to rounding conventions (e.g. 99.9 vs 100.0)
7. If the data is insufficient to check a particular item, note it in
   `overall_consistency_comment` rather than forcing a flag

## Severity Definitions

- `"critical"` — the contradiction materially changes a project-level conclusion
  (e.g. NPV sign, economic viability, resource category classification)
- `"significant"` — the contradiction affects a reported metric but does not change
  the overall conclusion (e.g. NPV differs by 15%, same project stage)
- `"minor"` — rounding, formatting, or label inconsistency with no economic effect

## Economic Impact Definitions

- `"positive"` — if the higher/corrected value is accepted, the project looks better
- `"negative"` — if the higher/corrected value is accepted, the project looks worse
- `"neutral"` — the contradiction does not affect economic metrics
- `"mixed"` — the impact depends on which value is correct and cannot be determined
- `"unknown"` — insufficient context to assess direction

## Output Format

Return only valid JSON. Do not include markdown, explanation, or commentary outside
the JSON object.

```json
{
  "contradictions": [
    {
      "contradiction_type": "string — one of: numeric_mismatch | arithmetic_error | logical_inconsistency | temporal_inconsistency | classification_mismatch",
      "description": "string — plain-language description of the contradiction",
      "location_a": "string — where the first value appears (section name, table name, or quote)",
      "value_a": "string — the first stated value",
      "location_b": "string — where the second value appears",
      "value_b": "string — the second stated value",
      "correct_value": "string or null — if an arithmetic error, show the correct calculation; otherwise null",
      "severity": "critical | significant | minor",
      "economic_impact": "positive | negative | neutral | mixed | unknown",
      "resolution_required": "string — what the analyst should do to resolve this"
    }
  ],
  "arithmetic_errors": [
    {
      "field": "string — what was calculated incorrectly",
      "stated_value": "string",
      "calculated_value": "string",
      "formula_used": "string — show the arithmetic",
      "discrepancy_pct": "number or null"
    }
  ],
  "contradiction_count": "integer",
  "critical_count": "integer",
  "significant_count": "integer",
  "minor_count": "integer",
  "overall_consistency_comment": "string — 2–4 sentence summary of the document's overall internal consistency, noting any systemic issues"
}
```
