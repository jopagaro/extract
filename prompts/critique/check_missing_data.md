# Task Prompt — Data Gap Report

You are reviewing source documents for a mining project technical study.
Your job is to identify every material data gap — information that is absent,
incomplete, or of insufficient quality to support the conclusions being drawn.

## Instructions

- Work through every analytical domain listed below
- For each gap, explain why it matters and what decision it affects
- Distinguish gaps that BLOCK advancement to the next study level from those that merely add uncertainty
- Do not flag trivial or administrative absences — only material gaps
- If a domain has no gaps, include it with gap_description: "No material gaps identified"
- Base your assessment entirely on what IS and IS NOT present in the source documents
- Do not assume data exists if it is not explicitly shown

## Urgency Definitions

- `"critical"` — must be addressed before advancing to the next study level; blocks the study
- `"important"` — should be addressed but does not block advancement; increases uncertainty
- `"minor"` — would improve confidence but has limited impact on key conclusions

## Assessment Domains

Assess each of the following domains:

1. **Geological data** — drill hole spacing and density, lithological logging, structural data, geotechnical data, QA/QC protocols
2. **Resource estimate** — classification basis (measured/indicated/inferred), estimation methodology, cut-off grade justification, validation
3. **Metallurgical testwork** — scale and representativeness of testwork, recovery assumptions, variability samples
4. **Mine planning** — design maturity, geotechnical inputs, mine scheduling, equipment selection basis
5. **Processing design** — flowsheet maturity, equipment sizing basis, reagent consumption data
6. **Infrastructure** — power source and cost, water supply, road access, tailings facility design, waste management
7. **Environmental and permitting** — baseline environmental studies, impact assessment status, permit timeline, closure plan
8. **Social and community** — community consultation records, IBA or similar agreements, social license status
9. **Economic inputs** — cost estimate class, price deck source and justification, contingency basis
10. **Financial model** — discount rate justification, tax model, sensitivity ranges, financing plan

## Output Format

Return ONLY valid JSON matching this structure exactly:

```json
{
  "data_gaps": [
    {
      "domain": "Domain name",
      "gap_description": "Plain-language description of what is missing or incomplete",
      "impact_on_analysis": "What conclusion or calculation is affected and how",
      "blocking_advancement": true,
      "recommended_action": "What should be done to address this gap",
      "urgency": "critical"
    }
  ],
  "critical_gaps_count": 0,
  "important_gaps_count": 0,
  "minor_gaps_count": 0,
  "overall_data_quality_comment": "A single plain-language paragraph summarising the overall state of data completeness for this project at its current study stage."
}
```
