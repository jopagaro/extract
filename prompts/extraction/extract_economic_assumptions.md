# Task Prompt — Extract Economic Assumptions

Extract the economic assumptions and input parameters used in the financial model
of this mining project. These are the numbers that feed the DCF — not the outputs.

## Instructions

- Extract only values explicitly stated in the document
- Do not calculate or derive values not directly stated
- Record units exactly as written — do not convert
- Record the source page or section for every value
- Use null for any field not found in the document

<!-- ✏️ EDIT: Add any firm-specific fields your models require (e.g. streaming terms, royalty buyback provisions) -->

## Output Format

```json
{
  "commodity_prices": [
    {
      "commodity": null,
      "price": null,
      "unit": null,
      "basis": null,
      "source_page": null
    }
  ],
  "exchange_rates": [
    {
      "pair": null,
      "rate": null,
      "basis": null,
      "source_page": null
    }
  ],
  "discount_rate_percent": null,
  "discount_rate_basis": null,
  "royalty_rate_percent": null,
  "royalty_type": null,
  "corporate_tax_rate_percent": null,
  "withholding_tax_percent": null,
  "depreciation_method": null,
  "depreciation_period_years": null,
  "inflation_rate_percent": null,
  "working_capital_days": null,
  "closure_provision": {
    "amount": null,
    "unit": null,
    "timing": null,
    "source_page": null
  },
  "smelter_terms": {
    "treatment_charge": null,
    "refining_charge": null,
    "payable_percent": null,
    "source_page": null
  },
  "price_deck_scenario": null,
  "study_date_prices": null,
  "notes": null,
  "sources": []
}
```

## Field Definitions

- `commodity_prices` — the long-term price assumptions used in the financial model (not spot)
- `basis` — e.g. "consensus analyst forecasts", "3-year trailing average", "company assumption"
- `discount_rate_basis` — e.g. "WACC", "hurdle rate", "industry convention"
- `royalty_type` — NSR (net smelter return), gross revenue, net profit, government, etc.
- `depreciation_method` — straight-line, units of production, declining balance
- `price_deck_scenario` — base case, upside, downside, spot — as labelled in the document
- `study_date_prices` — the spot prices at time of study (if stated separately from assumptions)

<!-- ✏️ EDIT: If your firm uses specific price deck scenarios (e.g. Wood Mackenzie, consensus), add instructions here for how the model should label them -->

## Important

Commodity price assumptions are the single largest driver of NPV sensitivity.
If multiple price scenarios are stated, extract all of them separately.
If the price assumption is not explicitly stated, record null — do not use current spot price as a proxy.
