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

## Important

Do NOT use numbered ratings or levels to characterise quality or confidence
(e.g. do NOT write "Level 2 data quality" or "confidence level 3").
Describe the actual situation in plain language — e.g. "the drill database is
insufficient to support Measured classification" or "sample preparation procedures
are consistent with industry practice."

## Output Format

Return a flat JSON object. Each field is a full prose paragraph for that sub-topic.
Use null for any field where source data is too sparse to write meaningfully.
Do not invent content.

```json
{
  "regional_setting": null,
  "local_geology": null,
  "mineralisation": null,
  "exploration_history": null,
  "drilling": null,
  "resource_estimate": null
}
```

## Sub-section Writing Guidelines

**regional_setting** — Place the project within its broader geological province.
Name the relevant cratons, terranes, belts, or basins. 2–4 sentences.

**local_geology** — Describe the stratigraphy, structure, and alteration at deposit
scale. Be specific about rock types and their relationships to mineralisation.

**mineralisation** — Describe ore type, mineralogy, grade distribution, and the
structural or lithological controls. State the deposit model.

**exploration_history** — Summarise work history: who did what and when.
Note previous resource estimates and their current status.

**drilling** — State total holes, metres, average spacing, orientations, and the
database size used for resource estimation.

**resource_estimate** — Describe the estimation method, domain model, software,
and qualified person. Present the resource statement if data is available, including
classification, effective date, cut-off grade, and any material caveats.

## Tone

Technical and precise. State uncertainties clearly — do not paper over data gaps.
The reader should finish this section with an accurate picture of what is known
and what is not.
