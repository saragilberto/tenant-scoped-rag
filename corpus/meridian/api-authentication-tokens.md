---
title: "Managing API Authentication Tokens"
category: "API"
version: "1.4"
visibility: restrito
---

API tokens are created from the developer settings screen and are shown in full only once, at
creation time; afterward only the last four characters remain visible for identification. A token
inherits the permission scope of the member who created it, so a token created by a Sales Rep cannot
read records that rep could not otherwise see, even if the API request itself is technically valid.
Revoking a token takes effect within a few seconds and cannot be undone — a revoked token's identifier
cannot be reactivated, and any integration using it must be reconfigured with a newly created token.
Tokens do not expire automatically by default, but a workspace owner can set a maximum token lifetime
in the security settings, after which every token past that age stops working until rotated.
