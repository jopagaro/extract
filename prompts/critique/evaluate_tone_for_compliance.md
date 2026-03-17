# Task Prompt — Evaluate Tone for Compliance

Review the generated report sections for compliance with the firm's language standards.
Identify any language that is promotional, investment-oriented, or inconsistent
with the neutral technical reporting standard required.

## Instructions

- Read every sentence in the report for tone violations
- Flag language that implies investment attractiveness, share price upside, or company promotion
- Flag superlatives and hyperbole that are not supported by specific data
- Flag any statement that could be construed as investment advice
- Do not flag factual positive statements that are clearly supported by data

<!-- ✏️ EDIT: Add your firm's specific banned language list here.
     Below is a generic list — replace or extend it with your internal compliance standards.
     e.g. If your firm operates under ASX/TSX/SEC regulations, add the specific
     disclosure rules that apply. Add your compliance officer's list of flagged phrases. -->

## Banned Language Categories

**Investment language** (always flag):
- "attractive investment", "compelling opportunity", "re-rate potential"
- "undervalued", "buy", "accumulate", "strong buy", "target price"
- "return to shareholders", "share price", "market cap upside"
- Predictions of share price performance

**Promotional superlatives** (flag if unsupported by data):
- "world-class", "tier-1", "exceptional", "outstanding", "best-in-class"
- "transformational", "company-maker", "game-changing"
- "significant", "impressive", "remarkable" (when applied to project metrics)
- "low-cost", "high-grade" (without a specific benchmark comparison)

**Compliance-sensitive language**:
- Forward-looking statements not accompanied by appropriate qualifications
- Production or cost guidance stated as fact rather than study estimate
- Claims about future permitting or regulatory outcomes stated as certain

## Output Format

```json
{
  "compliance_flags": [
    {
      "flagged_text": null,
      "location": null,
      "violation_category": null,
      "reason": null,
      "suggested_replacement": null
    }
  ],
  "investment_language_count": null,
  "promotional_language_count": null,
  "overall_compliance_status": null,
  "compliance_comment": null
}
```

## Overall Compliance Status

`"pass"` — no material violations found
`"review_required"` — minor issues that should be edited before publication
`"fail"` — material violations that must be corrected before the report is used

<!-- ✏️ EDIT: Define what constitutes pass/review_required/fail for your firm.
     e.g. "Any single investment language flag = fail. Any promotional superlative
     without data support = review_required." -->
