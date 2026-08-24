---
title: "Subscribing to Billing Webhooks"
category: "Integrations"
version: "1.6"
visibility: departamentos
---

## Event types

Halcyon fires webhook events for invoice creation, payment success, payment failure, and subscription
cancellation. Each event carries the full resource state at the time of the event, not just a
notification that something changed.

## Verifying authenticity

Every webhook request includes a signature header derived from a shared secret generated per
endpoint. Requests without a valid signature should be rejected outright, since the webhook endpoint
URL itself is public and not a secret.

## Retry schedule

A failing endpoint is retried at 1 minute, 5 minutes, 30 minutes, and 6 hours after the original
attempt. After the fourth failure the event is marked permanently failed and must be manually
replayed from the webhook logs screen rather than being retried further automatically.

## Payment failure specifics

The payment failure event includes a decline reason code from the payment processor, which is useful
for deciding whether to retry the charge automatically or to notify the customer that their card
needs updating.
