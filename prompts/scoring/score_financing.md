# Task Prompt — Score Financing

Assess the financing risk and bankability of this mining project.

## Instructions

- Assess the project's ability to attract debt and equity financing
- Evaluate the capital structure implied or stated in the project data
- Flag any gap between the financing requirement and the project's likely financing capacity
- Do not recommend specific lenders, investors, or financing structures

<!-- ✏️ EDIT: Add financing assessment factors specific to your firm's coverage.
     e.g. "Always assess eligibility for export credit agency (ECA) financing."
     or "Add DSCR (Debt Service Coverage Ratio) thresholds your firm uses
     to assess debt capacity." Add your benchmark NPV/CAPEX ratios here. -->

## Assessment Factors

1. **Capital requirement scale** — is the CAPEX within a range typically financed at this project stage?
2. **NPV/CAPEX ratio** — does the project generate sufficient returns to attract capital?
3. **Cash flow quality** — how stable and predictable are the projected cash flows for debt servicing?
4. **Offtake security** — are there binding offtake agreements that would support project finance?
5. **Sponsor capacity** — does the developer appear capable of funding their equity contribution?
6. **Jurisdiction risk** — does the country risk profile allow standard project finance terms?
7. **Streaming/royalty exposure** — is there existing or anticipated streaming/royalty financing?
8. **Contingency adequacy** — is the cost contingency sufficient to prevent budget overrun risk to lenders?
9. **Permitting completeness** — are the key permits in hand (required by lenders before financial close)?
10. **Independent technical review** — is there evidence of independent engineer engagement?

<!-- ✏️ EDIT: Add your firm's financing benchmarks:
     e.g. "For projects below USD 200M CAPEX, comment on junior equity financing feasibility.
     For projects above USD 500M CAPEX, assess project finance suitability." -->

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
  "overall_financing_comment": null
}
```

## Status Values

`"present"` | `"partial"` | `"missing"` | `"conflicting"` | `"unverifiable"`

## Economic Direction

`"positive"` | `"negative"` | `"neutral"` | `"mixed"`
