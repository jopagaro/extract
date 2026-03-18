# Task Prompt — Write Economics Section

Write the financial analysis section of the technical report for this mining project.

## Input

You will receive:
- DCF model outputs (NPV, IRR, payback at multiple discount rates)
- CAPEX schedule (initial, sustaining, closure)
- OPEX breakdown (mining, processing, G&A, unit costs)
- Revenue model (production schedule, commodity prices, payable metal, royalties)
- Sensitivity analysis results
- Economic assumptions

## Instructions

- Present numbers exactly as produced by the model — do not round selectively
- Always state the discount rate when quoting NPV
- Always state the price assumption when quoting revenue or NPV
- Present both pre-tax and post-tax results if available
- Do not describe the economics as "attractive" or "strong" — let the numbers speak

<!-- ✏️ EDIT: Specify your economics section structure and any mandatory disclosures.
     e.g. "Always include a sensitivity table showing NPV at ±20% on commodity price,
     CAPEX, and OPEX. Always state the basis for the discount rate.
     Include a cash flow waterfall chart description if chart_builder is available."
     Add your firm's conventions for presenting pre-tax vs post-tax results. -->

## Important

Do NOT use numbered ratings or levels to characterise financial strength or risk
(e.g. do NOT write "risk level 3" or "economic strength: 4/5").
If the economics are thin, say why — e.g. "the IRR of 8% falls below the typical
cost of capital for a project at this stage." If they are robust, say why.

## Output Format

Return a flat JSON object. Each field is a full prose paragraph for that sub-topic.
Also include a key_metrics array if hard figures are available.
Use null for any field where source data is insufficient. Do not invent numbers.

```json
{
  "economic_overview": null,
  "capital_costs": null,
  "operating_costs": null,
  "revenue_model": null,
  "project_economics": null,
  "sensitivity_analysis": null,
  "key_metrics": [
    {"metric": null, "value": null, "unit": null, "notes": null}
  ]
}
```

## Sub-section Guidelines

<!-- ✏️ EDIT: Replace with your firm's economics section writing standards -->

**Economic Overview**: Lead with NPV and IRR at the base case. State study level, date, and authors.

**Capital Cost Summary**: Total initial CAPEX by major category. Contingency allowance.
Sustaining capital over mine life. Closure provision.

**Operating Cost Summary**: Total AISC or unit OPEX. Breakdown by mining, processing,
G&A, and any other material categories. Note basis ($/t milled, $/oz produced, etc.)

**Revenue Model**: Annual production profile, head grade, recovery, payable metal,
price assumptions, smelter terms (if applicable), and royalty deductions.

**Project Economics**: Present NPV and IRR table at multiple discount rates.
State pre-tax and post-tax results. State payback period (simple and discounted).

**Sensitivity Analysis**: State NPV and IRR sensitivity to the top variables.
Typically: commodity price, CAPEX, OPEX, exchange rate, head grade. State the
range tested (typically ±10-30%).

**Tax and Fiscal Terms**: Describe the tax regime, royalty structure, depreciation
method, and any deferred taxes or loss carry-forwards.

## Tone

Analytical and balanced. Present the economics accurately under stated assumptions.
Explicitly note where assumptions are management estimates vs. independently confirmed.
