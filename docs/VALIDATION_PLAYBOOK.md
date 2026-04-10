# Validation Playbook

## Goal
Verify extraction quality against source messages before CRM upload.

## Checklist
- Compare `property_id` with source code value.
- Confirm `owner_name` and `owner_contact` pair.
- Validate `area` and `address` alignment.
- Check `sub_property_type` and `size`.
- Confirm `rent_or_sell_price` and `deposit`.
- Verify `tenant_preference`, `floor`, and `rent_sold_out`.

## Fast QA Steps
1. Paste message batch in app.
2. Process with AI fallback disabled.
3. Export CSV and review audit table.
4. Re-run with AI fallback enabled for failed/suspicious rows.
5. Compare corrected CSV with source text before final usage.
