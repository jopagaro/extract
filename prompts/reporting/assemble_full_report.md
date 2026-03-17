# Task Prompt — Assemble Full Report

Assemble all generated report sections into a complete, coherent technical report.

## Input

You will receive the following pre-written sections:
- Executive Summary
- Methodology
- Geology Section
- Mine Design / CAD Section
- Economics / Financial Analysis Section
- Risks and Uncertainties Section
- Appendices

## Instructions

- Review each section for internal consistency — numbers must match across sections
- Flag any contradictions between sections (e.g. NPV stated differently in exec summary vs body)
- Ensure the report flows logically from introduction through to conclusions
- Check that all figures cited in the executive summary are consistent with the body
- Do not rewrite sections — flag issues for review

<!-- ✏️ EDIT: Specify your complete report structure and numbering convention.
     e.g.:
     1. Executive Summary
     2. Introduction and Project Overview
     3. Geology and Mineral Resources
     4. Mine Planning and Design
     5. Metallurgy and Processing
     6. Infrastructure
     7. Capital Cost Estimate
     8. Operating Cost Estimate
     9. Financial Analysis
     10. Risks and Uncertainties
     11. Conclusions and Recommendations
     Appendices A–H

     Also specify your report title format, disclaimer text, and page numbering convention. -->

## Output Format

```json
{
  "report_title": null,
  "project_name": null,
  "prepared_by": null,
  "date": null,
  "study_level": null,
  "disclaimer": null,
  "table_of_contents": [
    {"section_number": null, "heading": null, "page_estimate": null}
  ],
  "consistency_issues": [
    {
      "issue": null,
      "section_a": null,
      "section_b": null,
      "conflicting_values": null
    }
  ],
  "sections_assembled": [],
  "report_ready": null
}
```

<!-- ✏️ EDIT: Replace the disclaimer field below with your firm's standard legal disclaimer.
     This is the disclaimer that appears on every report your firm produces. -->

## Standard Disclaimer

```
<!-- ✏️ EDIT: Insert your firm's legal disclaimer here.
     Example: "This report has been prepared by [Firm Name] for internal research purposes only.
     It does not constitute investment advice. [Firm Name] is not a registered investment adviser.
     Recipients should conduct their own due diligence before making any investment decision."
     Replace this entire block with your actual disclaimer text. -->
```

## Tone

The final assembly pass is a quality control step. Flag problems clearly.
A report with consistency issues should not be marked `report_ready: true`.
