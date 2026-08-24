---
title: "Bulk-Importing Customers via CSV"
category: "Data Import"
version: "1.8"
visibility: empresa
---

## File requirements

Halcyon accepts CSV files up to 20,000 rows for customer import, requiring a "Customer Name" column
and at least one billing contact reference column. Files missing either are rejected before any row
is read.

## Currency column

Every imported customer needs a currency code matching Halcyon's supported list; rows with an
unsupported or missing currency code are skipped and listed in the post-import summary rather than
defaulting to the workspace's base currency, since silently guessing a currency for billing data is
considered too risky.

## Duplicate customers

A row is treated as an existing customer when the customer name and tax identifier match exactly.
Matching rows update the existing customer's contact details but never change already-issued invoices
tied to that customer.

## Partial failures

Malformed rows do not stop the batch. They appear in a downloadable failure report naming the row
number and the specific validation that failed, so only the failed rows need correcting before a
follow-up import.
