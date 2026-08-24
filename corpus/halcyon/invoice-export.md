---
title: "Exporting Invoices in Bulk"
category: "Billing"
version: "2.1"
visibility: empresa
---

## Selecting invoices

The invoices screen supports filtering by date range, status, and customer before exporting, and the
export always reflects the filtered set shown on screen rather than requiring a separate confirmation
of which invoices are included.

## Export formats

Invoices can be exported as a combined PDF bundle for archival, or as a CSV with one row per invoice
for reconciliation in spreadsheet tools. The CSV format includes tax breakdown columns that the PDF
bundle does not, since the PDF is meant for human reading rather than reconciliation.

## Large exports

Exports covering more than 2,000 invoices are queued and delivered as a download link by email rather
than generated immediately, and the link expires after 48 hours for security, after which the export
must be requested again.

## Voided invoices

Voided invoices are included in exports by default but flagged with a status column; they are not
silently dropped, since accounting reconciliation typically needs to see voided invoices to explain
gaps in the invoice number sequence.
