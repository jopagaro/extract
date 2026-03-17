# Task Prompt — Summarize Economics

Write a concise technical summary of the financial model outputs for this mining project.

The input will be structured economic data — NPV, IRR, payback, CAPEX, OPEX,
production schedule, revenue model, and sensitivity results.

## Instructions

- Write in plain technical English suitable for a PEA, PFS, or FS-style report
- State all figures with their units and the assumptions they depend on
- Do not editorialize — report what the model shows, not whether the project is attractive
- Flag any assumptions that are unsupported or that materially drive the result
- Do not use investment language

<!-- ✏️ EDIT: Specify your preferred summary length and structure.
     e.g. "Write 4-6 paragraphs covering: project economics overview, capital cost summary,
     operating cost structure, production schedule highlights, sensitivity to key variables."
     Add your firm's discount rate convention and price deck reference here. -->

## Output Format

```json
{
  "economics_overview": null,
  "capex_summary": null,
  "opex_summary": null,
  "production_summary": null,
  "revenue_summary": null,
  "sensitivity_summary": null,
  "key_value_drivers": [],
  "key_economic_risks": [],
  "assumptions_flagged": [],
  "word_count": null
}
```

## Writing Standards

<!-- ✏️ EDIT: Replace with your firm's economic writing standards.
     Example conventions below — adjust to match your house style. -->

- **Economics overview**: Lead with NPV and IRR at the base case discount rate. State the study level and date.
- **CAPEX summary**: Total initial capital, sustaining capital, and closure provision. Note contingency allowance.
- **OPEX summary**: Life-of-mine unit cost ($/t milled or $/oz) and the main cost drivers.
- **Production summary**: Annual throughput, mine life, average head grade, and average recovery.
- **Revenue summary**: Average annual revenue, primary commodity price assumption, any by-product credits.
- **Sensitivity summary**: Identify the top 2-3 variables by NPV impact. State the range tested.
- **Key value drivers**: What are the 3-5 factors that most determine whether this project creates value?
- **Key economic risks**: What are the scenarios where the economics deteriorate materially?
- **Assumptions flagged**: Any assumption in the model that appears unsupported, optimistic, or not industry-standard.

## Tone

Analytical and neutral. Present both upside and downside scenarios evenhandedly.
Never describe NPV, IRR, or payback as "attractive", "compelling", or "strong"
without qualifying under what assumptions.
