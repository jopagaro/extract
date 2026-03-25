# Task Prompt — Extract Mineral Resource Table

Extract all mineral resource and mineral reserve estimates from the documents provided.

## Instructions

- Extract only what is explicitly stated — do not calculate or infer figures
- Preserve original units exactly as stated
- Capture every classification row separately (Measured, Indicated, Inferred, Proven, Probable)
- If multiple domains or zones are reported separately, capture each as its own row
- Use null for any field not present
- Record the source location for the table

## Output Format

Return a JSON object with this exact structure:

```json
{
  "rows": [
    {
      "classification": "Measured",
      "domain": null,
      "tonnage_mt": null,
      "grade_value": null,
      "grade_unit": null,
      "contained_metal": null,
      "metal_unit": null,
      "cut_off_grade": null,
      "notes": null,
      "source_page": null,
      "source_section": null
    }
  ],
  "qualified_person": null,
  "effective_date": null,
  "standard": null,
  "not_found": false
}
```

## Field Definitions

- `classification` — Measured, Indicated, Inferred, Proven, Probable, or Total
- `domain` — ore zone, mineralisation domain, or deposit name if reported separately (e.g. "oxide", "sulphide", "Main Zone")
- `tonnage_mt` — tonnes in millions (Mt) — convert if reported in other units
- `grade_value` — numeric grade value only, units in grade_unit
- `grade_unit` — g/t (grams per tonne), % (percent), ppm, lb/t, oz/t
- `contained_metal` — total metal content as a number
- `metal_unit` — Moz (million ounces), Mlb (million pounds), kt (thousand tonnes), Koz
- `cut_off_grade` — the cut-off grade used (e.g. "0.3 g/t Au")
- `standard` — reporting standard: NI 43-101, JORC, SAMREC, SEC SK-1300, or other
- `not_found` — set to true only if no resource estimate exists anywhere in the documents

## Important

- If a "Total" row summarises Measured + Indicated, capture it as classification = "Total M+I" or "Total"
- Do not duplicate data — if a total row is shown, capture it but do not re-add the component rows if already captured
- If no resource table is present in any document, set not_found to true and return an empty rows array
