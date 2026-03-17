# Task Prompt — Challenge Assumptions

Identify and challenge the key assumptions embedded in this mining project's
technical study. Focus on assumptions that are either unsupported by the data
or that, if wrong, would materially change the project economics.

## Instructions

- Find every major assumption in the project data — stated and implied
- For each assumption, assess whether it is supported, conservative, aggressive, or unknown
- Focus on assumptions with material economic consequences
- Suggest what data or analysis would be needed to validate or refute each assumption
- Do not be contrarian for its own sake — only challenge assumptions where there is a genuine basis

<!-- ✏️ EDIT: Add assumption categories specific to the project types you evaluate.
     e.g. "Always challenge the assumed metallurgical recovery if only bottle-roll tests exist."
     or "Always challenge grid power cost assumptions if the grid connection is unconfirmed."
     Add your firm's list of commonly optimistic assumptions in this commodity sector. -->

## Common Assumption Categories to Challenge

- Commodity price deck (vs. consensus, spot, long-term analyst forecasts)
- Metallurgical recovery (vs. testwork scale and completeness)
- CAPEX estimate accuracy class (vs. engineering maturity)
- OPEX unit costs (vs. regional operating analogues)
- Production ramp-up profile (vs. industry norms for this mine type and scale)
- Mining dilution and ore loss (vs. stated assumptions and geological complexity)
- Exchange rate assumptions (vs. forward curves or purchasing power parity)
- Discount rate (vs. market cost of capital for this risk profile)
- Royalty and tax treatment (vs. jurisdiction fiscal regime)
- Water, power, and logistics costs (vs. actual confirmed supply agreements)

## Output Format

```json
{
  "challenged_assumptions": [
    {
      "assumption": null,
      "stated_value": null,
      "basis_given": null,
      "challenge_basis": null,
      "direction_of_risk": null,
      "materiality": null,
      "validation_required": null,
      "source_page": null
    }
  ],
  "most_consequential_assumption": null,
  "overall_assumption_quality_comment": null
}
```

## Direction of Risk

`"upside"` — if wrong, the economics improve
`"downside"` — if wrong, the economics deteriorate
`"uncertain"` — direction not determinable from available data

## Materiality

`"high"` — >10% NPV impact if assumption is wrong by a reasonable amount
`"medium"` — 3-10% NPV impact
`"low"` — <3% NPV impact
`"unknown"` — cannot be estimated without sensitivity data

<!-- ✏️ EDIT: Replace the materiality thresholds above with your firm's standard
     sensitivity thresholds (e.g. your firm may use 5% and 15% as breakpoints) -->
