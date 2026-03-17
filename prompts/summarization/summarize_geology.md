# Task Prompt — Summarize Geology

Write a concise technical summary of the geological setting, mineralisation,
and resource base for this mining project.

The input will be structured geological data extracted from technical documents —
drill results, resource estimates, domain classifications, and geological interpretations.

## Instructions

- Write in plain technical English suitable for a PEA, PFS, or FS-style report
- Do not invent or infer data not present in the input
- Use past tense for completed work (drilling, sampling) and present tense for current status
- Round figures appropriately — match precision to the confidence level of the data
- Cite source documents or datasets where referenced

<!-- ✏️ EDIT: Specify the section length your reports typically use for geology summaries
     e.g. "Write 3-5 paragraphs" or "Maximum 600 words". Also add any house-style
     conventions: use of headings, NI 43-101 vs JORC language preferences, etc. -->

## Output Format

Return a structured JSON object with prose sections as string values:

```json
{
  "regional_setting": null,
  "local_geology": null,
  "mineralisation_style": null,
  "deposit_model": null,
  "exploration_history": null,
  "drilling_summary": null,
  "resource_summary_text": null,
  "data_quality_comment": null,
  "key_geological_risks": [],
  "word_count": null
}
```

## Writing Standards

<!-- ✏️ EDIT: Replace this section with your firm's specific writing standards.
     The examples below are generic placeholders — adjust tone, vocabulary,
     and technical detail level to match your typical output. -->

- **Regional setting**: 1–2 sentences placing the project within its tectonic and stratigraphic context
- **Local geology**: Describe host rocks, structures, alteration, and their relationship to mineralisation
- **Mineralisation style**: Identify the deposit model and controls on grade distribution
- **Drilling summary**: State number of holes, total metres, spacing, and any notable results
- **Resource summary text**: Summarise the resource estimate in plain language — category, tonnage, grade, contained metal
- **Data quality comment**: Note QA/QC status, sample intervals, laboratory used, and any flagged issues
- **Key geological risks**: List the main geological uncertainties that affect the resource estimate

## Tone

Neutral, technical, and factual. Avoid promotional language.
Do not use phrases like "world-class", "exceptional", "high-grade" without supporting data.
