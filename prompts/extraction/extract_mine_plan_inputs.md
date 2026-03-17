# Task Prompt — Extract Mine Plan Inputs

Extract the mine plan and production schedule parameters from this document.

## Output Format

```json
{
  "mine_type": null,
  "mining_method": null,
  "mine_life_years": null,
  "throughput": {
    "value": null,
    "unit": null,
    "basis": null
  },
  "strip_ratio": {
    "value": null,
    "unit": null
  },
  "production_schedule": [
    {
      "year": null,
      "ore_tonnes": null,
      "ore_grade_primary": null,
      "ore_grade_unit": null,
      "waste_tonnes": null,
      "contained_metal": null,
      "contained_metal_unit": null
    }
  ],
  "mining_rate": {
    "ore_per_day": null,
    "total_material_per_day": null,
    "unit": null
  },
  "equipment": {
    "primary_fleet": null,
    "fleet_size": null
  },
  "preproduction_period_months": null,
  "ramp_up_period_months": null,
  "sources": []
}
```

## Field Definitions

- `mining_method` — e.g. conventional truck-and-shovel, longhole stoping, sublevel caving, room-and-pillar
- `throughput.basis` — whether throughput is stated as ore processed, ore mined, or total material
- `strip_ratio.unit` — waste:ore (by tonnes), or total material:ore — preserve as stated
- `preproduction_period_months` — time from construction start to first ore
- `ramp_up_period_months` — time from first ore to full production rate

## Notes

If only an average annual production figure is given (not a full schedule), record it
as a single row with year set to "average" and note the lack of a full schedule.
