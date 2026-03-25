# Task Prompt — Extract Royalties and Streaming Agreements

Extract all royalty, streaming, and net profits interest agreements from the documents provided.

## Instructions

- Extract only what is explicitly stated — do not infer terms not present in the text
- Capture every distinct royalty or streaming agreement as a separate item
- Include agreements mentioned in legal schedules, title documents, disclosure sections, or technical report appendices
- Use null for any field not present
- Record the source location for each agreement found

## Output Format

Return a JSON object with this exact structure:

```json
{
  "agreements": [
    {
      "royalty_type": null,
      "holder": null,
      "rate_pct": null,
      "metals_covered": null,
      "area_covered": null,
      "stream_pct": null,
      "stream_purchase_price": null,
      "stream_purchase_unit": null,
      "sliding_scale_notes": null,
      "production_rate": null,
      "production_unit": null,
      "buyback_option": false,
      "buyback_price_musd": null,
      "recorded_instrument": null,
      "notes": null,
      "source_page": null,
      "source_section": null
    }
  ],
  "not_found": false
}
```

## Field Definitions

- `royalty_type` — one of: NSR (net smelter return), GR (gross royalty), NPI (net profits interest), Stream, Sliding NSR, Production, Other
- `holder` — the royalty or stream holder (company or individual name)
- `rate_pct` — percentage rate for NSR, GR, NPI, or Sliding NSR royalties
- `metals_covered` — which metals are subject to the royalty (e.g. "Gold, Silver" or "All metals")
- `area_covered` — which claims, tenements, or zones the royalty applies to
- `stream_pct` — for streaming agreements: percentage of production delivered to the streamer
- `stream_purchase_price` — fixed ongoing purchase price paid by the streamer
- `stream_purchase_unit` — unit for stream_purchase_price (e.g. USD/oz, USD/lb)
- `sliding_scale_notes` — describe the tiers if the royalty rate changes with commodity price
- `production_rate` — for per-unit production royalties: the dollar amount per unit
- `production_unit` — unit for production_rate (e.g. USD/oz, USD/t)
- `buyback_option` — true if the company has an option to buy back the royalty
- `buyback_price_musd` — buyback price in millions USD if stated
- `recorded_instrument` — title or agreement reference number/name
- `not_found` — set to true only if the documents contain no mention of royalties or streams

## Important

- If the documents explicitly state "no royalties" or "royalty free", return not_found = true with an empty agreements array and note this in the first agreement's notes field
- Government/state royalties (e.g. a country's standard mining royalty) should be recorded under royalty_type = "GR" with holder = the government entity — these are distinct from private royalties
- Do not duplicate — each agreement should appear only once
