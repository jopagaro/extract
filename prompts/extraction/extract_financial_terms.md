# Task Prompt — Extract Financial Terms

Extract the capital cost, operating cost, and key economic assumptions from this document.

## Output Format

```json
{
  "capex": {
    "initial_capex": null,
    "initial_capex_unit": null,
    "sustaining_capex_total": null,
    "sustaining_capex_per_year": null,
    "sustaining_capex_unit": null,
    "closure_cost": null,
    "closure_cost_unit": null,
    "contingency_percent": null,
    "accuracy_range": null,
    "effective_date": null,
    "capex_breakdown": []
  },
  "opex": {
    "total_cash_cost": null,
    "total_cash_cost_unit": null,
    "aisc": null,
    "aisc_unit": null,
    "mining_cost": null,
    "processing_cost": null,
    "ganda_cost": null,
    "cost_unit": null,
    "basis": null
  },
  "economics": {
    "commodity_price_assumptions": [],
    "exchange_rate_assumptions": [],
    "discount_rate_percent": null,
    "npv": null,
    "npv_unit": null,
    "irr_percent": null,
    "payback_years": null,
    "after_tax": null
  },
  "royalties": [],
  "taxes": {
    "corporate_tax_rate_percent": null,
    "jurisdiction": null,
    "notes": null
  },
  "sources": []
}
```

## Field Definitions

- `capex.accuracy_range` — stated accuracy e.g. "±25%" or "±15%" — indicates study level rigour
- `opex.basis` — per tonne ore, per tonne total material, per oz produced — preserve as stated
- `opex.aisc` — All-In Sustaining Cost if stated
- `opex.ganda` — general and administrative cost
- `economics.after_tax` — whether NPV and IRR are stated on an after-tax basis (true/false/null)
- `commodity_price_assumptions` — list of `{"commodity": "...", "price": ..., "unit": "...", "basis": "..."}`
- `royalties` — list of `{"type": "...", "rate": ..., "basis": "...", "payable_to": "..."}`

## Important

CAPEX and OPEX are among the most material figures in any economic study.
If a figure appears in multiple places with different values, extract all instances
and flag the discrepancy in the sources array.
Record the effective date of the cost estimate — costs stated in an old study may
not reflect current conditions.
