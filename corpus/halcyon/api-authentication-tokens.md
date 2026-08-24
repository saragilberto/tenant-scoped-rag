---
title: "Managing API Keys for Billing Integrations"
category: "API"
version: "1.2"
visibility: restrito
---

Halcyon API keys are scoped at creation to either read-only or read-write access, and a read-only key
cannot later be upgraded to read-write; a new key must be issued instead. The full key value is shown
exactly once, immediately after creation, and afterward only a short prefix remains visible for
identifying which key is which in logs and integration configuration. Because API keys can create
invoices and issue refunds when granted read-write access, Halcyon logs every action taken by a key
with the key's identifier rather than attributing the action to a generic "API" actor, keeping the
audit trail consistent with actions taken by human billing admins. A key can be paused temporarily
without revoking it permanently, which is useful while investigating suspicious activity without
having to reconfigure every integration that depends on it afterward.
