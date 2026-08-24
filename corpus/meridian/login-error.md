---
title: "Troubleshooting Sign-In Failures in Meridian"
category: "Account & Security"
version: "1.2"
visibility: empresa
---

## Common causes

Most sign-in failures in Meridian fall into three buckets: an expired session cookie, a workspace
that was renamed after the last login, or a browser extension blocking third-party cookies. Before
opening a support ticket, clear the site data for your Meridian workspace domain and try again in a
private browsing window.

## Checking your workspace status

If the private window still shows "workspace not found", your workspace subdomain may have changed
during a recent rebrand. Ask a workspace owner to confirm the current subdomain from the admin
settings screen, then update any bookmarked links.

## Repeated lockouts

Five failed attempts within ten minutes triggers a fifteen-minute cooldown on the account, shown as
a countdown on the sign-in screen. This is separate from two-factor lockouts, which are covered in
the two-factor authentication article. If the cooldown never expires, the account itself may have
been suspended by an administrator, and only a workspace owner can lift that suspension.

## When single sign-on is involved

Workspaces with SSO enabled route all sign-in attempts through the identity provider. A failure at
this stage almost always originates on the identity provider's side rather than in Meridian; check
the SSO setup article for the handshake steps Meridian expects.
