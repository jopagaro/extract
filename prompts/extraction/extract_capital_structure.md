# Task Prompt — Extract Capital Structure and Ownership

Extract the capital structure, share ownership, and financial encumbrances on this
mining project. An investor needs to understand how much of the upside is already
pledged to others and how much dilution is baked into the structure.

## Instructions

- Extract only what is explicitly stated in the document
- Record all share counts, warrant terms, and option details exactly as stated
- Note all royalty, streaming, earn-in, or off-take agreements that affect project economics
- Flag any debt facilities, covenants, or conditions that could constrain the company
- Use null for any field not found in the document

## Output Format

```json
{
  "shares": {
    "issued_outstanding": null,
    "fully_diluted": null,
    "unit": null,
    "as_of_date": null,
    "source_page": null
  },
  "warrants": [
    {
      "quantity": null,
      "exercise_price": null,
      "currency": null,
      "expiry_date": null,
      "source_page": null
    }
  ],
  "options": [
    {
      "quantity": null,
      "exercise_price": null,
      "currency": null,
      "expiry_date": null,
      "source_page": null
    }
  ],
  "royalties": [
    {
      "holder": null,
      "royalty_type": null,
      "rate": null,
      "metals_covered": null,
      "buyback_right": null,
      "source_page": null
    }
  ],
  "streaming_agreements": [
    {
      "counterparty": null,
      "metal": null,
      "stream_percent": null,
      "upfront_payment": null,
      "ongoing_price": null,
      "source_page": null
    }
  ],
  "earn_in_agreements": [
    {
      "partner": null,
      "earn_in_percent": null,
      "spend_commitment": null,
      "conditions": null,
      "source_page": null
    }
  ],
  "debt_facilities": [
    {
      "lender": null,
      "facility_type": null,
      "amount": null,
      "currency": null,
      "interest_rate": null,
      "maturity_date": null,
      "key_covenants": null,
      "source_page": null
    }
  ],
  "offtake_agreements": [
    {
      "counterparty": null,
      "metal": null,
      "volume_commitment": null,
      "pricing_basis": null,
      "term_years": null,
      "source_page": null
    }
  ],
  "major_shareholders": [
    {
      "name": null,
      "ownership_percent": null,
      "source_page": null
    }
  ],
  "capital_required_to_build": {
    "amount": null,
    "currency": null,
    "basis": null,
    "source_page": null
  },
  "funding_status": null,
  "notes": null,
  "sources": []
}
```

## Field Definitions

- `shares.fully_diluted` — total shares if all warrants, options, and convertibles are exercised
- `royalties.buyback_right` — whether the company has the right to repurchase the royalty, at what price
- `streaming_agreements.ongoing_price` — the per-ounce or per-pound price paid to the company under the stream after delivery
- `funding_status` — plain English description: e.g. "Fully funded to production", "Requires $120M equity raise", "Funded to PFS completion only"

## Important

Royalty stacks, streaming agreements, and warrant overhangs are the most common
ways junior mining upside is silently capped. A company with 3% NSR + 2% royalty
+ a silver stream has already pledged a large share of its economics.
Extract every encumbrance mentioned, no matter how it is labelled.
