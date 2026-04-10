# Troubleshooting

## Common Issues

### Rent appears as wrong large number
- Cause: malformed input or prior parser version.
- Fix: update parser and reprocess. Ensure message includes each lead boundary.

### Deposit missing
- Check if deposit is unlabeled numeric line or month-based (`2 Month`).
- Enable AI fallback to repair uncertain rows.

### Area mismatch
- Provide custom area file in sidebar if dataset differs.
- Verify area spellings and locality aliases.

### Tenant preference empty
- Ensure phrases like `Family`, `Bachelors`, or `All` are present in message body.

### Non-WhatsApp tabular rows
- Keep one row per line with tab separators.
- Include owner, phone, Sell/Rent, area/address, price, BHK, and size if possible.
