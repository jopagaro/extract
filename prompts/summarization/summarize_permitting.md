# Task Prompt — Summarize Permitting Status

Write a concise technical summary of the permitting and regulatory status
for this mining project.

## Instructions

- Summarize the current permitting position clearly and accurately
- State what permits are held, what is pending, and what is still required
- Note any material conditions, timelines, or obligations
- Flag any permit that is on the critical path to construction or production
- Do not speculate about approval outcomes

<!-- ✏️ EDIT: Add the jurisdiction-specific context your analysts need.
     e.g. "Always note whether an Indigenous Land Use Agreement (ILUA) is required
     under Australian Native Title Act." or "Flag if a Chilean DGA water right
     is provisional or definitive." -->

## Output Format

```json
{
  "permitting_overview": null,
  "permits_held": null,
  "permits_pending": null,
  "permits_required": null,
  "critical_path_permits": [],
  "key_conditions": null,
  "social_licence_status": null,
  "permitting_timeline_comment": null,
  "key_permitting_risks": [],
  "word_count": null
}
```

## Writing Standards

<!-- ✏️ EDIT: Replace with your firm's permitting section conventions -->

- **Permitting overview**: 1-2 sentences on the overall permitting status and jurisdiction framework
- **Permits held / pending / required**: Bullet-style or prose — be specific about which permits, not just counts
- **Critical path permits**: Any permit whose absence would prevent construction or production from commencing
- **Key conditions**: Ongoing obligations (monitoring, reporting, bonding, closure fund contributions)
- **Social licence status**: Community support level and any formal agreements in place
- **Permitting timeline**: Estimated time to full permitting based on stated timelines or jurisdiction norms

## Tone

Factual and specific. Permitting sections are often where project-fatal risks hide.
Do not use vague language like "permitting is progressing well" without evidence.
