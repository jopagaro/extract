# Task Prompt — Write Risk Section

Write the risks and uncertainties section of the technical report for this mining project.

## Input

You will receive:
- Risk summary narrative
- Structured risk list (category, description, economic direction, mitigation)
- Top risks identified by the risk assessor
- Data gaps summary

## Instructions

- Present all material risks — do not omit risks that make the project look less favourable
- For each risk, describe: what it is, why it matters, what the potential impact is, and what (if any) mitigation exists
- Use the same risk categories consistently throughout the section
- Flag risks that are on the critical path to a final investment decision

<!-- ✏️ EDIT: Specify your risk section structure and any mandatory risk disclosures.
     e.g. "Always include a separate paragraph on sovereign/country risk."
     or "List risks in order of materiality, not category."
     Add any risk factors that are mandatory disclosures for your jurisdiction or client type. -->

## Output Format

```json
{
  "section_title": "Risks and Uncertainties",
  "risk_overview_paragraph": null,
  "risk_subsections": [
    {
      "category": null,
      "heading": null,
      "text": null
    }
  ],
  "data_gaps_paragraph": null,
  "word_count": null
}
```

## Writing Standards

<!-- ✏️ EDIT: Replace with your firm's risk section conventions -->

**Risk overview**: 1-2 sentences introducing the risk landscape.
State the number of material risk categories identified.

**Per-category paragraphs**: Each risk category gets one paragraph.
State: the specific risks in that category, why they are material to this project,
the potential economic impact (qualitatively), and what mitigation is in place.

**Data gaps**: A closing paragraph identifying what information is missing that,
if available, would materially change the risk picture.

## Tone

Honest and specific. Risk sections are often written to comfort rather than inform.
This section should leave the reader with an accurate picture of the downside scenarios.
Do not use language that minimizes a risk unless the mitigation genuinely addresses it.
