# Task Prompt — Confidence Assessment

You are reviewing a mining project technical analysis to assess how much confidence
should be placed in each section of the report and in the overall conclusions.

This is NOT a score. Do not use numbers, ratings, percentages, or scales.
Describe confidence in plain language — what the evidence supports and what it does not.

## What Drives Confidence

Higher confidence comes from:
- Multiple independent sources that agree on the same figures
- Data that has been independently verified or audited
- Assumptions that are clearly stated and supported
- Consistency between different sections of the report

Lower confidence comes from:
- A single unverified source for a key figure
- Assumptions that are stated without basis
- Contradictions between documents
- Key data that is absent and has been estimated or assumed
- Vague or qualitative descriptions where quantitative data is needed

## Instructions

Assess confidence for each domain listed below. For each:
- Write a plain-language confidence descriptor (one sentence — what level of trust is warranted and why)
- List the main factors that support confidence
- List the main factors that limit confidence
- If confidence is high, say so clearly and explain what makes it reliable
- If confidence is low, say so clearly and explain what is missing or uncertain
- Do not soften or hedge — be direct

## Domains to Assess

1. **Geology and resource estimate** — how reliable is the resource base?
2. **Metallurgy and recovery** — how well supported are the processing assumptions?
3. **Mine planning and schedule** — how credible is the production plan?
4. **Capital cost estimate** — how well-founded are the capex figures?
5. **Operating cost estimate** — how well-founded are the opex figures?
6. **Economic projections** — how reliable are the NPV, IRR, and payback figures?
7. **Market and price assumptions** — how reasonable are the commodity price inputs?
8. **Environmental and permitting** — how much certainty exists on approvals?
9. **Overall report conclusions** — how much trust should be placed in the top-level findings?

## Output Format

Return ONLY valid JSON matching this structure exactly:

```json
{
  "domain_confidence": [
    {
      "domain": "Domain name",
      "confidence_descriptor": "One clear sentence stating what level of confidence is warranted and why",
      "supporting_factors": ["Factor 1", "Factor 2"],
      "limiting_factors": ["Factor 1", "Factor 2"]
    }
  ],
  "overall_confidence_statement": "A single plain-language paragraph describing the overall reliability of this report's conclusions — what can be trusted, what cannot, and why.",
  "most_reliable_aspect": "The single aspect of this report that rests on the strongest evidential basis",
  "least_reliable_aspect": "The single aspect of this report that rests on the weakest evidential basis"
}
```
