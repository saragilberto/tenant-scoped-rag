---
title: "Fixing Login Errors on Halcyon"
category: "Account & Security"
version: "1.1"
visibility: empresa
---

## The "session expired" message

Halcyon signs users out after ninety minutes of inactivity on shared or public devices, and after
fourteen days on devices marked "trusted" at login. Seeing "session expired" repeatedly on a device
you use daily usually means the "remember this device" checkbox was left unticked.

## Billing admin lockout

An account with the billing admin role that fails to sign in five times in a row is locked for
thirty minutes, longer than the lockout applied to regular members, because billing admin accounts
can move money and warrant a stricter cooldown.

## Wrong workspace redirect

Typing the wrong workspace slug in the URL redirects to a generic "workspace not found" screen rather
than revealing whether that slug belongs to another customer, which is intentional: confirming a
slug's existence would leak which companies use Halcyon.

## SSO-enabled workspaces

If your workspace has single sign-on configured, password-based login is disabled entirely and any
login attempt with a password will fail regardless of whether the password is correct — see the SSO
setup article for how the handshake is supposed to work instead.
