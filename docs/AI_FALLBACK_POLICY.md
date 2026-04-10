# AI Fallback Policy

## Principle
Rule-based extraction is primary. AI correction is optional and conservative.

## When AI is Called
- Rows with missing important fields.
- Rows flagged as suspicious by validator heuristics.

## What AI Can Correct
- owner_name, owner_contact
- area, address
- rent, deposit
- tenant_preference, size, floor
- rent_sold_out, property_type (only when evidence is stronger)

## Guardrails
- Batch requests to reduce cost and latency.
- Merge AI output into blanks or suspicious fields only.
- Preserve deterministic fields when confidence is high.
