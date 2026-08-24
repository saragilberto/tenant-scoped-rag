---
title: "Processing a Customer Refund"
category: "Billing"
version: "1.4"
visibility: restrito
---

## Full versus partial refunds

A refund can be issued for the full invoice amount or for a specific line item, and partial refunds
automatically recalculate the tax portion proportionally rather than requiring the tax to be refunded
as a separate manual step.

## Processing time

Refunds are submitted to the original payment processor immediately but typically take five to ten
business days to appear on the customer's statement, a delay controlled by the card network rather
than by Halcyon.

## Refunding to store credit instead

Rather than returning funds to the original payment method, a refund can be issued as account credit,
which applies automatically to the customer's next invoice and never expires unless the account
itself is closed.

## Audit trail

Every refund records the issuing billing admin, the reason code selected from a required dropdown,
and an optional free-text note, all of which appear in the immutable audit log covered in the log
retention article.
