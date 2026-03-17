# Task Prompt — Extract CAD Model Semantics

Extract structured information about the 3D models, mine designs, and CAD
objects present in the mining project data provided.

The input will be a text description of a CAD model — extracted layer names,
object types, bounding coordinates, mesh statistics, and design metadata.

## Instructions

- Extract only what is explicitly present in the model description
- Record layer names and object types exactly as labelled in the CAD file
- Record dimensions in the units stated — do not convert
- Use null for any field not found
- If no interpretable design information is present, return null for all fields

<!-- ✏️ EDIT: Add object type mappings specific to the software your projects use
     e.g. Leapfrog, Vulcan, Datamine, Surpac, Micromine layer naming conventions.
     Add any specific object categories you want extracted or highlighted. -->

## Output Format

```json
{
  "model_type": null,
  "software_origin": null,
  "coordinate_system": null,
  "units": null,
  "bounding_box": {
    "x_min": null, "x_max": null,
    "y_min": null, "y_max": null,
    "z_min": null, "z_max": null
  },
  "layers": [
    {
      "layer_name": null,
      "object_type": null,
      "object_count": null,
      "interpretation": null
    }
  ],
  "pit_design": {
    "present": null,
    "pit_name": null,
    "bench_height_m": null,
    "overall_slope_angle_deg": null,
    "berm_width_m": null
  },
  "underground_design": {
    "present": null,
    "access_type": null,
    "level_spacing_m": null,
    "development_metres": null
  },
  "waste_dump": {
    "present": null,
    "capacity_m3": null,
    "footprint_ha": null
  },
  "tailings_facility": {
    "present": null,
    "capacity_m3": null,
    "footprint_ha": null
  },
  "infrastructure_features": [],
  "notes": null,
  "sources": []
}
```

## Layer Interpretation

For each layer, attempt to classify `interpretation` using one of:
- `"ore_body"`, `"pit_design"`, `"underground_workings"`, `"topography"`,
  `"waste_dump"`, `"tailings"`, `"infrastructure"`, `"haul_road"`,
  `"processing_plant"`, `"camp"`, `"power_line"`, `"water_feature"`,
  `"exploration_target"`, `"unknown"`

<!-- ✏️ EDIT: Add interpretation categories for any mine infrastructure types
     specific to the commodities or regions your firm covers -->

## Important

If the CAD description is sparse or difficult to interpret, extract what is
available and set `notes` to explain the limitations.
