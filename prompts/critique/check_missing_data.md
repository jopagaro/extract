# Task Prompt — Check Missing Data

Identify all material data gaps in the project dataset — information that is absent,
incomplete, or of insufficient quality to support the conclusions drawn.

## Instructions

- Work through every analytical domain: geology, mining, metallurgy, infrastructure, environment, economics
- For each gap identified, state why it matters and what decision it affects
- Distinguish between gaps that block advancement and gaps that introduce uncertainty
- Do not flag trivial or administrative absences

<!-- ✏️ EDIT: Add data gap categories specific to the study levels your firm typically evaluates.
     e.g. "For a PEA, a missing hydrogeological study is a gap but not necessarily blocking.
     For a FS, it is blocking." Specify your thresholds for what constitutes a material gap
     vs. an acceptable uncertainty at each study level. -->

## Assessment Domains

For each domain below, assess what data is present, partial, or absent:

1. **Geological data** — drill spacing, lithological logging, structural data, geotechnical data
2. **Resource estimate** — classification adequacy, estimation methodology, validation
3. **Metallurgical testwork** — scale of testwork, variability samples, locked cycle tests
4. **Mine planning** — design stage, geotechnical inputs, mine scheduling basis
5. **Processing design** — flowsheet maturity, equipment selection, vendor quotes
6. **Infrastructure** — power, water, roads, tailings, waste dumps — confirmed vs assumed
7. **Environmental** — baseline studies, impact assessment, closure plan
8. **Social and permitting** — consultation records, permit status, community agreements
9. **Economic inputs** — cost estimate basis, price deck source, tax model basis
10. **Financial model** — sensitivity analysis, scenario analysis, financing plan

<!-- ✏️ EDIT: Add domain-specific data requirements for the commodity types you cover.
     e.g. For gold heap leach: "Column leach tests at representative particle size."
     For underground: "Geotechnical drilling for stope stability analysis." -->

## Output Format

```json
{
  "data_gaps": [
    {
      "domain": null,
      "gap_description": null,
      "impact_on_analysis": null,
      "blocking_advancement": null,
      "recommended_action": null,
      "urgency": null
    }
  ],
  "critical_gaps_count": null,
  "overall_data_quality_comment": null
}
```

## Urgency Values

`"critical"` — must be addressed before advancing to the next study level
`"important"` — should be addressed but does not block advancement
`"minor"` — would improve confidence but has limited impact on conclusions
