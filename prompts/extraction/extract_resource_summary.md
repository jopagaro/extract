# Task Prompt — Extract Resource Summary

Extract the mineral resource and reserve estimate from this document.

## Instructions

- Extract figures exactly as stated — do not recalculate or convert
- Record the classification system used (JORC, NI 43-101, PERC, etc.)
- Record the effective date of the estimate
- Record the cut-off grade and basis for cut-off
- If multiple estimates exist (e.g. different dates or consultants), extract all of them
- If the document contains only a summary table, extract from the table

## Output Format

```json
{
  "classification_system": null,
  "effective_date": null,
  "qualified_person": null,
  "cut_off_grade": {
    "value": null,
    "unit": null,
    "basis": null
  },
  "resources": [
    {
      "category": null,
      "tonnes": null,
      "tonnes_unit": null,
      "grade_primary": null,
      "grade_primary_unit": null,
      "contained_metal_primary": null,
      "contained_metal_primary_unit": null,
      "grade_secondary": null,
      "grade_secondary_unit": null,
      "source_page": null,
      "source_table": null
    }
  ],
  "reserves": [
    {
      "category": null,
      "tonnes": null,
      "tonnes_unit": null,
      "grade_primary": null,
      "grade_primary_unit": null,
      "contained_metal_primary": null,
      "contained_metal_primary_unit": null,
      "source_page": null,
      "source_table": null
    }
  ],
  "total_resource_tonnes": null,
  "total_resource_contained_primary": null,
  "notes": null
}
```

## Field Definitions

- `category` — Measured, Indicated, Inferred (resources) or Proven, Probable (reserves)
- `tonnes_unit` — Mt (million tonnes), kt (thousand tonnes), or t (tonnes) — preserve as stated
- `grade_primary_unit` — g/t, %, ppm, ppb, lb/t — preserve as stated
- `contained_metal_primary_unit` — Moz, koz, oz, Mt, kt, t, Mlb — preserve as stated
- `qualified_person` — name and credentials of the QP who signed off the estimate
- `notes` — any material caveats, exclusions, or rounding notes stated in the document

## Important

Resource and reserve figures are among the most material facts in a mining report.
If there is any ambiguity about a number (e.g. it is unclear whether a figure is
total or per-category), flag it in the notes field rather than guessing.
