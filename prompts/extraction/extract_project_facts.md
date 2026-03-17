# Task Prompt — Extract Project Facts

Extract the core identifying facts about this mining project from the document provided.

## Instructions

- Extract only what is explicitly stated in the document
- Do not infer, calculate, or assume any value not present in the text
- For every field, record the source location (page number or section heading)
- Use null for any field not found in the document
- Preserve original units exactly as stated — do not convert

## Output Format

Return a JSON object with this exact structure:

```json
{
  "project_name": null,
  "operator": null,
  "project_location": {
    "country": null,
    "region_or_state": null,
    "nearest_town": null,
    "coordinates": null
  },
  "commodity_primary": null,
  "commodities_secondary": [],
  "deposit_type": null,
  "mine_type": null,
  "study_level": null,
  "study_date": null,
  "study_author": null,
  "project_status": null,
  "land_package": {
    "area_ha": null,
    "tenure_type": null,
    "ownership_percent": null
  },
  "sources": []
}
```

## Field Definitions

- `operator` — the company operating or developing the project
- `commodity_primary` — the main economic mineral (e.g. gold, copper, lithium)
- `commodities_secondary` — by-products or co-products with economic value
- `deposit_type` — geological classification (e.g. porphyry copper, orogenic gold, MVT zinc)
- `mine_type` — open pit, underground, heap leach, in-situ, placer, or combination
- `study_level` — scoping, PEA, PFS, FS, or historical
- `study_date` — date the study was published or completed
- `study_author` — consulting firm or individual who authored the study
- `project_status` — e.g. exploration, development, construction, production, care and maintenance
- `sources` — list of objects: `{"field": "...", "page": ..., "section": "..."}`

## Important

If the document does not contain enough information to extract any of these fields,
return the JSON with all fields set to null and include a note in the sources array
explaining what was found.
