# CSV Schema (Strict)

The output CSV follows this exact column order:

1. property_id
2. property_type
3. special_note
4. owner_name
5. owner_contact
6. area
7. address
8. sub_property_type
9. size
10. furnishing_status
11. availability
12. floor
13. tenant_preference
14. additional_details
15. age
16. rent_or_sell_price
17. deposit
18. date_stamp
19. rent_sold_out

## Notes
- `property_type` values: `Res_rental` or `Res_resale`
- `rent_or_sell_price` and `deposit` are numeric rupee values
- `date_stamp` is extracted from WhatsApp header when available
