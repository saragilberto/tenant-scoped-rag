---
title: "Exporting Deal Invoices from Meridian"
category: "Billing"
version: "1.1"
visibility: empresa
---

## Where invoices come from

Meridian does not generate invoices itself. Instead, once a deal reaches the "Closed Won" stage, its
line items become eligible for export into a format that most accounting tools can import: a flat
CSV with one row per line item, grouped by deal reference.

## Running an export

From the deals list, filter to "Closed Won" within the desired date range and choose "Export line
items" from the bulk actions menu. Exports larger than 5,000 line items are processed in the
background and delivered as a download link rather than an immediate file.

## Currency handling

Line items are exported in the currency the deal was created in, not converted to a workspace
default. Mixed-currency exports include a currency column per row so downstream accounting tools can
apply their own conversion rates rather than relying on a rate baked in at export time.

## Common export errors

An export fails outright only when a deal in the selected range has no line items at all, which
usually means the deal was closed manually without going through the standard quote flow. The error
report names the specific deals to fix before re-running the export.
