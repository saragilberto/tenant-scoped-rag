---
title: "Understanding Meridian API Rate Limits"
category: "API"
version: "3.1"
visibility: departamentos
---

## Default limits

Every Meridian API token is limited to 600 requests per minute, measured on a rolling sixty-second
window per token, not per workspace. Workspaces on the growth plan may request a higher ceiling from
their account manager.

## Reading the response headers

Every API response includes a remaining-requests header and a reset-time header. Clients that ignore
these and retry immediately on a 429 response tend to make the situation worse, since the retry
itself counts against the same window.

## Bulk endpoints

The contacts and deals bulk-export endpoints have a separate, stricter limit of 10 requests per
minute, because each call can return up to 10,000 records. This limit exists independently of the
600-per-minute general limit and is not shown in the standard rate-limit headers — it returns its own
distinct error code when exceeded.

## Recommended backoff

Meridian recommends exponential backoff starting at one second, doubling on each consecutive 429,
capped at thirty seconds between attempts. Clients that implement this pattern rarely hit the bulk
endpoint's stricter limit even under sustained load.
