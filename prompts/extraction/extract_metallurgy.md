# Task Prompt — Extract Metallurgy

Extract metallurgical testwork results, recovery assumptions, and processing parameters.

## Output Format

```json
{
  "process_route": null,
  "testwork_type": [],
  "head_grade_tested": {
    "value": null,
    "unit": null
  },
  "recoveries": [
    {
      "commodity": null,
      "recovery_percent": null,
      "basis": null,
      "testwork_type": null,
      "variability_tested": null
    }
  ],
  "concentrate": {
    "grade": null,
    "grade_unit": null,
    "mass_pull_percent": null,
    "payable_metals": []
  },
  "reagents": [],
  "water_consumption": {
    "value": null,
    "unit": null
  },
  "energy_consumption": {
    "value": null,
    "unit": null
  },
  "variability_tests": {
    "conducted": null,
    "domains_tested": null,
    "recovery_range": null,
    "notes": null
  },
  "metallurgical_risks": null,
  "sources": []
}
```

## Field Definitions

- `process_route` — e.g. "flotation + leach", "CIL", "heap leach", "gravity + flotation"
- `testwork_type` — list: e.g. ["bottle roll", "column leach", "flotation", "gravity"]
- `recoveries.basis` — on what basis recovery is stated: "on head", "on feed", "on circuit feed"
- `recoveries.variability_tested` — whether variability across domains was tested (true/false/null)
- `concentrate.payable_metals` — metals paid for in the concentrate (relevant for smelter terms)
- `variability_tests.recovery_range` — e.g. "82% to 94%" — the range across variability samples

## Notes

Recovery assumptions directly drive revenue in the economic model.
If only a single composite was tested, flag this in metallurgical_risks —
composites may not represent variability across the deposit.
