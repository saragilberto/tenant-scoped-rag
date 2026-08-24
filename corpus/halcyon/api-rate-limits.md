---
title: "Halcyon API Rate Limits Explained"
category: "API"
version: "2.4"
visibility: departamentos
---

## Standard limit

The Halcyon API allows 300 requests per minute per API key, tracked on a rolling window. This is
lower than many billing APIs because most Halcyon integrations are scheduled jobs rather than
interactive applications, and the limit is sized for that pattern.

## Invoice generation endpoint

Creating invoices through the API has its own limit of 60 per minute, separate from the general
limit, because invoice creation triggers downstream tax calculation that is more expensive to compute
than a typical read request.

## Webhook-driven design encouraged

Halcyon recommends subscribing to webhooks for state changes instead of polling the API for invoice
or subscription status, since polling at any meaningful frequency tends to consume a large share of
the 300-per-minute budget for no new information most of the time.

## Exceeding the limit

Exceeding either limit returns a 429 response with a retry-after header giving the exact number of
seconds to wait, which is more precise than the general rate-limit reset window and should be
preferred by clients that read it.
