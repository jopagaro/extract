# Task Prompt — Write Geology Section

Write the geology section of the technical report for this mining project.

## Input

You will receive:
- Extracted geological data (deposit type, host rocks, structure, alteration)
- Drillhole summary statistics (hole count, total metres, spacing)
- Resource estimate data
- Geological risk assessment
- Geological summary narrative

## Instructions

- Write in technical language appropriate for a PEA, PFS, or FS report
- Structure the section with clear sub-headings
- Describe mineralisation in terms of its controls — structural, stratigraphic, lithological
- Report drilling results factually — do not cherry-pick high-grade intercepts
- State data quality and QA/QC status honestly

<!-- ✏️ EDIT: Specify the sub-section structure your geology sections use.
     e.g. 3.1 Regional Geology / 3.2 Local Geology / 3.3 Mineralisation /
     3.4 Exploration History / 3.5 Drilling / 3.6 Sampling and QA/QC /
     3.7 Resource Estimation / 3.8 Resource Statement -->

## Output Format

```json
{
  "section_title": "Geology",
  "subsections": [
    {
      "heading": null,
      "level": null,
      "text": null
    }
  ],
  "word_count": null
}
```

## Sub-section Guidelines

<!-- ✏️ EDIT: Replace with your firm's geology section writing standards -->

**Regional Setting**: Place the project within its broader geological province.
Name the relevant cratons, terranes, belts, or basins. 2-3 sentences.

**Local Geology**: Describe the stratigraphy, structure, and alteration that host
the mineralisation at the deposit scale. Be specific about rock types and their relationships.

**Mineralisation**: Describe the ore type, mineralogy, grade distribution, and structural
or lithological controls. State the deposit model.

**Exploration History**: Summarise the history of work at the project — who did what, when.
Note any previous resource estimates and their status.

**Drilling**: State total holes, metres, spacing, orientations, and the extent of
the database used for resource estimation.

**Sampling and QA/QC**: Describe sample types, preparation, laboratory, and the QA/QC
program. Note any issues identified and how they were addressed.

**Resource Estimation**: Describe the estimation method, domain model, variography,
and validation approach. State the software and qualified person.

**Resource Statement**: Present the resource table. State the classification standard,
effective date, cut-off grade, and qualified person. Flag any material caveats.

## Tone

Technical and precise. The geology section is the foundation of the economic model.
State uncertainties clearly — do not paper over data gaps with confident-sounding prose.
