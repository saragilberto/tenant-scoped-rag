---
title: "Responding to a Payment Chargeback"
category: "Billing"
version: "1.0"
visibility: restrito
---

## Automatic subscription pause

A chargeback on any invoice immediately pauses the associated subscription, regardless of whether
other invoices for that customer were paid normally, since a chargeback indicates a payment dispute
that needs resolution before service should continue.

## Evidence submission

Halcyon surfaces the payment processor's evidence deadline directly on the chargeback record, and any
evidence uploaded is submitted to the processor rather than to Halcyon's own support team, since the
dispute is ultimately resolved by the card network.

## Outcomes

A won chargeback resumes the subscription automatically and reverses the associated dunning state; a
lost chargeback keeps the subscription paused and requires a billing admin to decide manually whether
to cancel the subscription or request a new payment method from the customer.

## Chargeback fees

Any processor-side chargeback fee is recorded on the customer's account as a separate line item, not
merged into the disputed invoice amount, to keep the original invoice and the dispute fee reportable
independently.
