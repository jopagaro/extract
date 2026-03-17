# Task Prompt — Score Permitting

Assess the permitting and regulatory position of this mining project.

## Instructions

- Evaluate the completeness and status of the permitting program
- Identify permits on the critical path to construction and production
- Assess social licence and community relations based on available data
- Flag any permitting risk that could materially delay or prevent the project

<!-- ✏️ EDIT: Add jurisdiction-specific permitting assessment criteria.
     e.g. "In Australia: always assess Native Title Act obligations."
     "In Canada: assess Crown consultation requirements."
     "In Latin America: assess prior consultation (consulta previa) requirements."
     Add country-specific timelines your firm uses as benchmarks. -->

## Assessment Factors

1. **Environmental assessment status** — is the EA/EIS complete, in progress, or not yet started?
2. **Construction permits** — are all required construction approvals held or on a clear timeline?
3. **Operating licence** — is the operating permit (mining lease, concession) secured?
4. **Water rights** — are water rights sufficient for the proposed operation?
5. **Land access** — is the surface access position resolved with landowners?
6. **Indigenous consultation** — has consultation been completed to the standard required?
7. **Social licence** — is there credible community support, or evidence of opposition?
8. **Permitting timeline** — is the timeline to full permitting realistic given the project schedule?
9. **Regulatory risk** — is there any indication of regulatory uncertainty or policy change risk?
10. **Compliance history** — is there any record of prior violations or enforcement actions?

<!-- ✏️ EDIT: Add specific permit types that are mandatory disclosures for your standard reports -->

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
  "overall_permitting_comment": null
}
```

## Status Values

`"present"` | `"partial"` | `"missing"` | `"conflicting"` | `"unverifiable"`

## Economic Direction

`"positive"` | `"negative"` | `"neutral"` | `"mixed"`

## Tone

Specific. Permitting assessments must identify which specific permits are at risk
and what that means for the construction or production timeline.
