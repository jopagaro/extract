# Task Prompt — Extract Operator and Management Track Record

Extract verifiable information about the people and company behind this mining project.
An investor needs to know whether this team has actually built and delivered mines before,
not just whether they make confident claims.

## Instructions

- Extract only what is explicitly stated in the document
- For each named individual, record what the document says about their background
- Flag any stated prior project — note whether it reached production or was sold/abandoned
- Do not infer success from titles — extract what is actually said
- Use null for any field not found in the document

## Output Format

```json
{
  "operator_company": {
    "name": null,
    "exchange_listed": null,
    "ticker": null,
    "market_cap_stated": null,
    "years_in_operation": null,
    "other_active_projects": [],
    "source_page": null
  },
  "management_team": [
    {
      "name": null,
      "title": null,
      "background_summary": null,
      "prior_projects": [
        {
          "project_name": null,
          "role": null,
          "outcome": null,
          "outcome_detail": null
        }
      ],
      "source_page": null
    }
  ],
  "board_members": [
    {
      "name": null,
      "relevant_experience": null,
      "source_page": null
    }
  ],
  "technical_advisors": [],
  "company_track_record": {
    "mines_built_to_production": null,
    "projects_permitted": null,
    "projects_sold_or_jv": null,
    "projects_abandoned": null,
    "notes": null
  },
  "key_risks_management": null,
  "sources": []
}
```

## Field Definitions

- `prior_projects.outcome` — use one of: `"production"`, `"sold"`, `"jv_partner"`, `"permitted"`, `"abandoned"`, `"still_active"`, `"unknown"`
- `prior_projects.outcome_detail` — e.g. "Sold to Barrick Gold for $340M in 2019", "Reached commercial production 2015, now in care and maintenance"
- `company_track_record.mines_built_to_production` — integer count of mines this company or its key people have taken from grassroots to production
- `key_risks_management` — any stated concerns about management depth, key-person risk, or succession

## Important

The single most predictive factor in junior mining success is whether the people running
the project have done it before. Extract every verifiable data point about prior delivery.
If the document contains biographies or a "management" section, extract all of it.
If it does not, record null — do not invent or infer credentials.
