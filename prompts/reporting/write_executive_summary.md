# Task Prompt — Write Executive Summary

Write the executive summary section of the technical report for this mining project.

The executive summary is the most-read section of any technical report. It must
stand alone — a reader who reads only this section must leave with an accurate
and complete picture of the project.

## Input

You will receive the following pre-summarised data:
- Project facts (name, location, commodity, study level)
- Resource and reserve summary
- Economics summary (NPV, IRR, CAPEX, OPEX, mine life)
- Key risks summary
- Permitting and development status

## Instructions

- Write in the third person, past and present tense as appropriate
- Do not introduce information not present in the input data
- Lead with what the project is, then what the study found, then the key risks
- Do not use investment language or promotional phrases
- Keep it concise — this section should be readable in under 5 minutes

<!-- ✏️ EDIT: Specify your target word count and structure.
     e.g. "Target 500-800 words. Use the following paragraph structure:
     1. Project description and location (2-3 sentences)
     2. Study scope and methodology (2-3 sentences)
     3. Resource/reserve summary (1 paragraph)
     4. Economic highlights under base case (1 paragraph)
     5. Key development risks (1 paragraph)
     6. Status and next steps (2-3 sentences)"
     Also specify whether to include a key metrics table. -->

## Output Format

```json
{
  "executive_summary_text": null,
  "key_metrics_table": [
    {"metric": null, "value": null, "unit": null, "assumption": null}
  ],
  "word_count": null
}
```

## Writing Standards

<!-- ✏️ EDIT: Replace with your firm's executive summary conventions.
     The paragraph guidance below is a generic template. -->

**Paragraph 1 — Project Identity**
State: project name, operator, location (country and region), primary commodity,
mine type, and study level.

**Paragraph 2 — Study Scope**
State: who prepared the study, when, at what confidence level, and what the
scope included (geology, mining, processing, infrastructure, economics).

**Paragraph 3 — Resource / Reserve**
State: the total resource and/or reserve, classification, effective date, and
the qualified person. Note the classification standard (NI 43-101 / JORC / PERC).

**Paragraph 4 — Economics**
State: pre-tax and post-tax NPV (at the stated discount rate), IRR, payback period,
initial CAPEX, life-of-mine OPEX (unit cost), and mine life. State the commodity
price assumption used.

**Paragraph 5 — Key Risks**
State the two or three risks that most materially affect the viability of the project.
Be specific.

**Paragraph 6 — Status and Next Steps**
State the current development status and what is required to advance the project.

## Tone

Neutral, factual, and balanced. An executive summary is not a pitch document.
The reader should be able to make an informed assessment from this section alone.
