# Task Prompt — Score Geology

Assess the quality and completeness of the geological data and resource estimate
for this mining project.

## Instructions

- Assess each factor listed below based on the geological data provided
- Write a plain-language assessment for each factor — no numeric scores
- State clearly what is known, what is missing, and what it means for the project
- Use the economic direction tags exactly as specified

<!-- ✏️ EDIT: Add or remove assessment factors to match your firm's geological due diligence checklist.
     e.g. add "geotechnical data adequacy" or "hydrogeological characterisation"
     if these are material to the project types you cover. -->

## Assessment Factors

For each factor below, produce one assessment object:

1. **Resource classification** — are the resource categories appropriate for the data density?
2. **Data density** — is the drill spacing adequate to support the stated classification?
3. **QA/QC program** — is there evidence of systematic quality control on sampling and assaying?
4. **Estimation method** — is the method (kriging, ID, etc.) appropriate for this deposit type?
5. **Geological model** — is the domain model geologically reasonable and internally consistent?
6. **Grade continuity** — is the grade distribution appropriate for the interpreted controls?
7. **Top-cutting** — has high-grade capping been applied, and is the basis stated?
8. **Reconciliation** — where applicable, how does the estimate reconcile with mine production?
9. **Qualified person** — is the QP independent, experienced, and appropriately credentialled?
10. **Resource growth potential** — is there credible upside beyond the current estimate?

<!-- ✏️ EDIT: Add any factor that is always relevant for your commodity focus.
     e.g. for gold: "Nugget effect and coarse gold handling"
     For lithium: "Brine vs. hard rock, evaporation pond assumptions"
     For copper: "Supergene vs. hypogene proportions and recovery implications" -->

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
  "overall_geology_comment": null
}
```

## Status Values

`"present"` | `"partial"` | `"missing"` | `"conflicting"` | `"unverifiable"`

## Economic Direction

`"positive"` | `"negative"` | `"neutral"` | `"mixed"`

## Tone

Direct and honest. The geology score informs the confidence level attached to
the resource estimate. Understate nothing.
