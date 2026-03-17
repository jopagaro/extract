# Task Prompt — Score Economics

Assess the quality and robustness of the economic analysis for this mining project.

## Instructions

- Assess each factor listed below based on the economic data provided
- Write a plain-language assessment for each factor — no numeric scores
- Focus on whether the economic inputs are supportable and the outputs are reliable
- Flag any assumption that appears optimistic, unsupported, or outside industry norms

<!-- ✏️ EDIT: Add assessment factors specific to your firm's economic due diligence process.
     e.g. add "streaming or royalty financing impact" or "sustaining capital adequacy"
     if these are areas where your firm applies particular scrutiny. -->

## Assessment Factors

1. **Commodity price assumptions** — are the price assumptions reasonable vs. consensus and spot?
2. **CAPEX estimate quality** — what is the accuracy class of the CAPEX estimate? Is contingency adequate?
3. **OPEX estimate quality** — are operating costs supported by testwork, analogues, or detailed engineering?
4. **Production schedule realism** — does the ramp-up and steady-state throughput reflect achievable rates?
5. **Recovery assumptions** — are metallurgical recoveries supported by testwork at appropriate scale?
6. **Royalty and fiscal treatment** — are all government and contractual royalties correctly modelled?
7. **Tax model** — is the corporate tax treatment correct for the jurisdiction and project structure?
8. **Discount rate basis** — is the discount rate stated, and is the basis (WACC, hurdle) explained?
9. **Closure provision** — is closure cost adequate and appropriately timed in the cash flow?
10. **Sensitivity analysis** — has sensitivity been run on the key value drivers at appropriate ranges?

<!-- ✏️ EDIT: Add commodity-specific factors:
     e.g. For gold: "AISC vs. all-in cost reconciliation"
     For base metals: "TC/RC terms and payable metal calculations"
     For lithium: "Hydroxide vs. carbonate pricing and offtake terms" -->

## Output Format

```json
{
  "assessments": [
    {
      "field": null,
      "status": null,
      "economic_direction": null,
      "assessment": null,
      "impacts": [],
      "recommended_action": null,
      "source": null
    }
  ],
  "overall_economics_comment": null
}
```

## Status Values

`"present"` | `"partial"` | `"missing"` | `"conflicting"` | `"unverifiable"`

## Economic Direction

`"positive"` | `"negative"` | `"neutral"` | `"mixed"`

## Tone

Rigorous. Economic assessments must not give unwarranted comfort.
Every significant assumption should be questioned.
