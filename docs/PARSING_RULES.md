# Parsing Rules Reference

## Field Rules
- `property_id`: from `Property Code`, else generated `PROP-XXXXXXXXXX`.
- `property_type`: inferred from Rental/Resale keywords.
- `owner_name`/`owner_contact`: label-aware and adjacency-aware extraction.
- `area`: area list lookup with partial + fuzzy fallback.
- `address`: rich assembled address with apartment/society context.
- `sub_property_type`: BHK/RK pattern extraction.
- `size`: line-level area parsing (`sq.ft`, `sqft`, `sft`, carpet/built-up).
- `rent_or_sell_price`: labeled first, then unlabeled money line fallback.
- `deposit`: labeled/secondary money line/month-based inference.
- `floor`: line-safe floor extraction (`Ground`, `3rd`, `2(Out of 4 Floors)`).
- `tenant_preference`: inferred from Family/Bachelors/All phrases.
- `rent_sold_out`: inferred from Rent Out / Sold Out phrases.

## Normalization
- whitespace cleanup
- title casing for names/status
- numeric conversion for money units (`K`, `Lac`, `Cr`)
