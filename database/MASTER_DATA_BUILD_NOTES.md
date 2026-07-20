# Master Data Module — Build Notes

## Authority rules

- The TMS controls route group, route cluster, referral rank, cadence, next due date, due status, routability, and exclusion reason.
- The current Doctor Spreadsheet refreshes factual doctor/practice/contact data, referral totals, notes, and last-visit dates when a matching doctor and address are found.
- One physical address is stored as one Practice.
- A Doctor may be associated with multiple Practices.
- Missing records are marked inactive rather than deleted.

## Current seed import validation

- 364 unique doctors
- 239 physical practice locations
- 365 doctor-practice associations
- 188 visit-history rows
- 1,092 annual referral snapshot rows (2024–2026)

The Streamlit Master Data tab can load these approved seed files into an empty database and can later refresh the database from a newly uploaded pair of authoritative files.
