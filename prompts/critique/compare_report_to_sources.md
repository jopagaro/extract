# Task Prompt — Compare Report to Sources

Verify that the statements and figures in the generated report are consistent
with the underlying source documents and extracted data.

This is a provenance check — every material claim in the report should be
traceable to a specific source document and page.

## Instructions

- Compare each major figure in the report against the extracted source data
- Flag any figure in the report that differs from the source extraction by more than rounding
- Flag any claim in the report that cannot be traced to a source
- Flag any source data that was extracted but not reflected in the report
- Do not flag minor formatting or rounding differences (e.g. 2.3 Mt vs 2.30 Mt)

<!-- ✏️ EDIT: Set your firm's tolerance for numerical differences.
     e.g. "Flag any difference greater than 1% between report figures and source data."
     or "Flag any NPV difference greater than USD 5M." -->

## Key Fields to Verify

- Resource and reserve tonnage, grade, and contained metal
- NPV, IRR, and payback period
- Initial CAPEX total
- Life-of-mine OPEX unit cost
- Mine life and annual production rate
- Commodity price assumptions
- Discount rate
- Royalty and tax rates
- Project location and commodity

## Output Format

```json
{
  "verified_fields": [
    {
      "field": null,
      "report_value": null,
      "source_value": null,
      "source_document": null,
      "source_page": null,
      "match_status": null,
      "discrepancy_note": null
    }
  ],
  "unverified_claims": [
    {
      "claim": null,
      "report_location": null,
      "reason_unverifiable": null
    }
  ],
  "source_data_not_reflected": [],
  "overall_provenance_comment": null
}
```

## Match Status Values

`"match"` — report value consistent with source within rounding
`"mismatch"` — report value differs from source beyond acceptable tolerance
`"not_found_in_source"` — figure appears in report but not in extracted source data
`"not_in_report"` — figure extracted from source but absent from report

<!-- ✏️ EDIT: Add any specific fields your reports always need to verify.
     e.g. "Always verify the Qualified Person name and credentials."
     or "Always verify the effective date of the resource estimate." -->
