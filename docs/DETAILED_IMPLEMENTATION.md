# Detailed Implementation Notes

## Overview
This app is designed as a rule-first extraction pipeline for WhatsApp and tabular lead messages.

Pipeline stages:
1. Input normalization and timestamp repair
2. Message splitting
3. Rule-based extraction
4. Validation and suspicious-field checks
5. Optional Groq fallback for correction
6. CSV shaping in strict output schema

## Core Parser Decisions
- Rule-based extraction is always primary.
- AI is optional and only used to repair missing or suspicious fields.
- Area matching uses deterministic substring checks before fuzzy matching.
- Address is assembled from nearby lines to preserve apartment/building context.

## Important Reliability Features
- Handles malformed timestamps and spacing.
- Prevents mobile numbers and years from being parsed as rent.
- Supports line-only money format (`7.5 K` on one line, `20 K` on next line).
- Supports deposit in month format (`2 Month`).
- Auto-assigns unique random IDs when property code is missing.
- Infers tenant preference from natural phrases (`Family Only`, `Bachelors`).

## Extensibility
- `parser.py` contains all extraction logic and should remain business-rule focused.
- `utils.py` contains reusable cleaning and matching primitives.
- `app.py` remains UI-only and calls parser methods as a black box.
