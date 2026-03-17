# Task Prompt — Extract Permitting and Regulatory Information

Extract all permitting, regulatory, environmental, and social licence information
from this mining project document.

## Instructions

- Extract only what is explicitly stated in the document
- Record permit names and reference numbers exactly as stated
- Note status: approved, applied for, pending, required but not yet applied, expired
- Record any conditions, timelines, or obligations attached to permits
- Use null for any field not found

<!-- ✏️ EDIT: Add jurisdiction-specific permit types relevant to your main operating regions
     e.g. Chilean DGA water rights, Australian EPBC approvals, Canadian EA certificates,
     Nevada NDEP, West African mining conventions, etc. -->

## Output Format

```json
{
  "jurisdiction": null,
  "regulatory_body": null,
  "environmental_assessment": {
    "required": null,
    "status": null,
    "reference": null,
    "decision_date": null,
    "conditions_count": null,
    "source_page": null
  },
  "permits": [
    {
      "permit_name": null,
      "permit_number": null,
      "issuing_authority": null,
      "status": null,
      "issue_date": null,
      "expiry_date": null,
      "conditions": null,
      "source_page": null
    }
  ],
  "water_rights": {
    "status": null,
    "volume": null,
    "unit": null,
    "source": null,
    "source_page": null
  },
  "land_access": {
    "status": null,
    "agreement_type": null,
    "parties": [],
    "source_page": null
  },
  "indigenous_consultation": {
    "required": null,
    "status": null,
    "outcome": null,
    "source_page": null
  },
  "social_licence": {
    "status": null,
    "community_agreements": [],
    "source_page": null
  },
  "key_risks": [],
  "estimated_permitting_timeline_months": null,
  "notes": null,
  "sources": []
}
```

## Status Values

Use only these values for `status`:
- `"approved"` — permit or approval is in hand
- `"applied"` — application submitted, decision pending
- `"required"` — identified as required but application not yet submitted
- `"not_required"` — explicitly confirmed as not applicable
- `"expired"` — previously held but lapsed
- `"unknown"` — document does not state

<!-- ✏️ EDIT: Add your firm's specific social or environmental scoring criteria here
     e.g. if your reports always reference IFC Performance Standards or Equator Principles -->

## Important

Permitting status is a key development risk driver.
Flag any permit that is required for construction or operation but has not yet been approved.
