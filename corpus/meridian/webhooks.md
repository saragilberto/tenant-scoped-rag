---
title: "Configuring Webhooks for Pipeline Events"
category: "Integrations"
version: "2.2"
visibility: departamentos
---

## Available events

Meridian can notify an external URL when a deal changes stage, when a new lead is created, or when a
contact is merged during deduplication. Each webhook subscription picks one event type; multiple
event types require multiple subscriptions.

## Delivery and retries

A webhook delivery is considered successful only on a 2xx response within five seconds. Failed
deliveries are retried up to four times with increasing delay, and a subscription that fails ten
consecutive deliveries is automatically paused until manually resumed from the integrations screen.

## Payload signing

Every webhook payload includes a signature header computed from a per-subscription secret shown once
at creation time. Receivers should verify this signature before trusting the payload, since the
webhook URL itself is not otherwise authenticated.

## Ordering is not guaranteed

Because retries can complete out of order relative to newer events, receivers should treat each
payload as a full snapshot of the entity at the time of the event rather than assuming events arrive
in the sequence they occurred.
