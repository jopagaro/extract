# Task Prompt — Write Appendix Content

Generate appendix content for the technical report — supporting tables, data
summaries, and reference material that is too detailed for the main body.

## Input

You will receive structured data from across the project:
- Full resource and reserve tables
- Detailed CAPEX line-item schedule
- Detailed OPEX breakdown
- Production schedule (year-by-year)
- Cash flow model (year-by-year)
- Sensitivity tables (full matrix)
- Source document list

## Instructions

- Format all tables clearly with headers, units, and totals
- Include a document reference list citing every source used in the report
- Label each appendix with a letter (Appendix A, Appendix B, etc.)
- Keep appendix content factual — no narrative interpretation here

<!-- ✏️ EDIT: Specify which appendices your standard report structure includes
     and in what order. e.g.:
     Appendix A — Mineral Resource Statement
     Appendix B — Mineral Reserve Statement
     Appendix C — Capital Cost Estimate
     Appendix D — Operating Cost Estimate
     Appendix E — Production Schedule
     Appendix F — Annual Cash Flow Model
     Appendix G — Sensitivity Analysis
     Appendix H — Source Documents
     Add or remove appendices to match your house style. -->

## Output Format

```json
{
  "appendices": [
    {
      "label": null,
      "title": null,
      "content_type": null,
      "table_headers": [],
      "rows": [],
      "notes": null
    }
  ]
}
```

## Content Types

- `"resource_table"` — mineral resource statement
- `"reserve_table"` — mineral reserve statement
- `"capex_table"` — capital cost estimate
- `"opex_table"` — operating cost breakdown
- `"production_table"` — year-by-year production schedule
- `"cashflow_table"` — annual cash flow model
- `"sensitivity_table"` — sensitivity matrix
- `"source_list"` — reference documents

## Tone

No narrative — tables and lists only. Precise and complete.
