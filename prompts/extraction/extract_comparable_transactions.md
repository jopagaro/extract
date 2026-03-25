# Task Prompt — Extract Comparable Transactions

Extract any merger, acquisition, royalty purchase, stream deal, or comparable transaction referenced in the documents provided.

## Instructions

- Extract transactions that are explicitly referenced to benchmark valuation or provide market context
- These typically appear in MD&A sections, valuation sections, or market comparable tables
- Also extract any transaction directly involving this project (e.g. a prior acquisition)
- Use null for any field not present
- Record the source location for each transaction

## Output Format

Return a JSON object with this exact structure:

```json
{
  "transactions": [
    {
      "project_name": null,
      "acquirer": null,
      "seller": null,
      "commodity": null,
      "transaction_date": null,
      "transaction_value_musd": null,
      "resource_moz_or_mlb": null,
      "price_per_unit_usd": null,
      "study_stage": null,
      "jurisdiction": null,
      "notes": null,
      "source_page": null,
      "source_section": null
    }
  ],
  "not_found": false
}
```

## Field Definitions

- `project_name` — name of the project or asset involved in the transaction
- `acquirer` — the buyer or acquiring company
- `seller` — the vendor or selling company
- `commodity` — primary commodity (e.g. gold, copper, silver)
- `transaction_date` — year or full date of the transaction (YYYY or YYYY-MM)
- `transaction_value_musd` — total deal value in millions USD
- `resource_moz_or_mlb` — total resource at time of transaction (Moz for gold, Mlb for copper)
- `price_per_unit_usd` — implied acquisition price per ounce or pound (USD/oz or USD/lb)
- `study_stage` — stage of the project at time of transaction: Exploration, PEA, PFS, FS, Producing
- `jurisdiction` — country or region of the project
- `not_found` — set to true if no comparable transactions are referenced anywhere in the documents

## Important

- Include both completed acquisitions and announced transactions if referenced
- If the document provides $/oz or $/lb metrics directly, use those — do not calculate
- If the transaction involves a royalty or stream (not an equity acquisition), note this in the notes field
- Streaming deals should use price_per_unit_usd as the ongoing purchase price, not the upfront payment
