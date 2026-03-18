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

## Important

Do NOT assign numbered severity ratings to risks (e.g. do NOT write "Risk Level 3"
or "severity: 4/5"). Describe each risk's materiality in plain language — explain
what the potential financial or operational impact is and whether any meaningful
mitigation exists. Describe intensity with words: "this risk could materially delay
the project" not "this is a Level 4 risk."

## Output Format

Return a flat JSON object. Each field is a full prose paragraph for that risk category.
Use null for categories not relevant to this project. Do not invent risks.

```json
{
  "risk_overview": null,
  "geological_risks": null,
  "technical_and_engineering_risks": null,
  "permitting_and_regulatory_risks": null,
  "financial_and_market_risks": null,
  "operational_risks": null,
  "data_gaps": null
}
```

## Writing Standards

**risk_overview** — 2–3 sentences summarising the overall risk picture.
Identify the most material categories without using numbered ratings.

**Per-category fields** — Each active risk category gets one prose paragraph.
State: the specific risks, why they matter to this project, the potential
economic impact in plain language, and what mitigation (if any) is in place.

**data_gaps** — Identify information that is absent from the source documents
that would materially change the risk picture if it were available.

## Tone

Honest and specific. Risk sections are often written to comfort rather than inform.
This section should leave the reader with an accurate picture of the downside scenarios.
Do not use language that minimizes a risk unless the mitigation genuinely addresses it.
