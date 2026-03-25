# Task Prompt — Extract Source Citations

You are a mining research analyst creating a source citation index for a technical report.
You have been given two things:
1. The source documents (labeled `[Source: filename]`) from which the report was generated
2. The report sections that were written from those source documents

Your job is to trace each material claim in the report back to the specific source document
and passage that supports it.

## What Counts as a Citable Claim

Cite specific, verifiable statements — not general observations. Priority claims to cite:

- Resource/reserve tonnage, grade, and contained metal figures
- NPV, IRR, payback period, and other economic outputs
- CAPEX and OPEX figures
- Commodity price assumptions
- Recovery rates
- Mine life and production rate
- Study classification (PEA / PFS / FS / scoping)
- Royalty rates, NSR terms, streaming agreements
- Permitting status and key approvals
- Key project dates (construction start, production start, closure)
- Technical certifications (QP name, 43-101 / JORC disclosure)
- Strip ratio, mining method, processing method

## How to Find Citations

The source documents are labeled with `[Source: filename]` headers in the input.
When you find a passage that supports a claim, quote the relevant sentence or phrase
exactly as it appears in the source. If a figure appears in a table, quote the table
heading and the relevant row. Include the section name or page reference if it can
be inferred from headings in the source text.

## Citation Confidence Levels

- `"direct"` — the exact claim appears verbatim or near-verbatim in the source
- `"inferred"` — the claim is derived from source data (e.g. calculated from two numbers that are both stated)
- `"not_found"` — the claim was made in the report but no supporting source passage was found; this is itself a finding worth flagging

## Instructions

1. Read the report sections in the `extra_context` to identify all citable claims
2. Search the source documents for passages that support each claim
3. For each claim, record the exact source file, a verbatim quote from the source,
   and a location reference (section heading, table name, page number) if visible
4. Assign a citation ID (C001, C002, …) to each citation
5. Flag any claim that cannot be traced to a source (confidence = "not_found") —
   this may indicate the LLM introduced a figure not present in the documents
6. Do NOT fabricate quotes. If you cannot find an exact supporting passage, use
   confidence = "inferred" (if derivable) or "not_found" (if not derivable)
7. Group citations by the report section they support

## Output Format

Return only valid JSON.

```json
{
  "citations": [
    {
      "citation_id": "C001",
      "section": "string — report section key, e.g. '03_geology' or '04_economics'",
      "claim": "string — the claim as stated in the report",
      "source_file": "string — the filename exactly as it appears in [Source: filename]",
      "source_quote": "string — verbatim excerpt from the source (max 200 chars)",
      "location_in_source": "string or null — section name, table name, or page reference if visible",
      "confidence": "direct | inferred | not_found"
    }
  ],
  "total_citations": "integer",
  "not_found_count": "integer — number of claims with no source support",
  "citation_coverage_comment": "string — 1–2 sentence summary of how well the report claims trace back to sources",
  "uncited_sections": ["string — section keys where no citations were found"]
}
```
