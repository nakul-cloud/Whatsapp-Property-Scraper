# Fix Changelog

## Major Functional Fixes Implemented

1. Added robust WhatsApp timestamp formatter before splitting.
2. Implemented safe bulk message splitting by timestamp boundaries.
3. Improved owner name/contact extraction for multiline and labeled variants.
4. Added deterministic + fuzzy Pune area matching.
5. Upgraded rich address extraction with apartment/society context.
6. Fixed size extraction for carpet/built-up/inline formats.
7. Fixed rent extraction from labeled and unlabeled money lines.
8. Added deposit extraction and month-multiplier support.
9. Implemented floor extraction for mixed textual formats.
10. Added auto random unique property ID generation when missing.
11. Added tenant preference inference from natural phrasing.
12. Added rent_sold_out derivation from listing status text.
13. Added suspicious-row detection for AI correction workflow.
14. Extended AI fallback merge to repair wrong values safely.
15. Added fallback parser for tab-separated non-WhatsApp lead formats.
16. Added failed-message audit table and CSV export in UI.
