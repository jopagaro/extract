# Task Prompt — Write Methodology Section

Write the methodology section of the technical report describing how the analysis
was conducted, what data was used, and what the limitations of the study are.

## Input

You will receive:
- Source document list and ingestion summary
- Extraction method descriptions
- Economic model parameters and assumptions
- Study level and scope

## Instructions

- Describe the analytical process clearly and transparently
- State the data sources and their dates
- Acknowledge limitations — what data was unavailable or assumed
- Write for an informed reader who wants to understand how the conclusions were reached

<!-- ✏️ EDIT: Specify your firm's methodology disclosure conventions.
     e.g. "State that this report was prepared using [Firm Name]'s proprietary
     analysis platform. Describe the dual-LLM extraction process if relevant
     to your disclosure requirements. Add any regulatory disclaimers required
     for your jurisdiction or study level." -->

## Output Format

```json
{
  "section_title": "Methodology and Data Sources",
  "subsections": [
    {
      "heading": null,
      "level": null,
      "text": null
    }
  ],
  "data_sources_list": [
    {"source_name": null, "date": null, "author": null, "relevance": null}
  ],
  "limitations_paragraph": null,
  "word_count": null
}
```

## Sub-section Guidelines

<!-- ✏️ EDIT: Replace with your firm's methodology section standards -->

**Study Scope**: Describe what the study covers and does not cover.
State the study level (scoping, PEA, PFS, FS) and its implications for confidence.

**Data Sources**: List and briefly describe each primary data source — technical reports,
drill databases, cost studies, price decks. Note the date of each source.

**Extraction and Analysis Process**: Describe at a high level how data was extracted,
normalised, and processed. Note any material assumptions made during data normalisation.

**Economic Model**: Describe the DCF framework — discount rate basis, tax treatment,
price deck, inflation assumptions.

**Limitations**: State clearly what data was not available, what was assumed,
and how these limitations affect the conclusions.

## Tone

Transparent and precise. The methodology section protects the report's credibility.
A reader who questions a conclusion should be able to trace it back through this section.
