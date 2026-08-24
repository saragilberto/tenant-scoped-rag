---
title: "Configuring Billing Role Permissions"
category: "Account & Security"
version: "1.3"
visibility: restrito
---

## Built-in roles

Halcyon ships with three built-in roles: Billing Admin, Finance Viewer, and Standard Member. Only
Billing Admin can issue refunds, credit notes, or change a customer's payment method; Finance Viewer
can see all billing data but cannot modify it.

## Custom roles

A workspace can clone Billing Admin or Finance Viewer into a custom role and remove specific
permissions, such as a "refund-only" role that can issue refunds but not credit notes, useful for
support staff who need limited billing capability without full admin access.

## Scope of Finance Viewer

Finance Viewer access can be scoped to specific customer segments rather than the entire customer
base, which is commonly used to give regional finance staff visibility only into their region's
accounts.

## Role changes and active sessions

Unlike some other settings, a role downgrade takes effect on the affected member's very next action
rather than waiting for their session to expire, since billing permissions are considered too
sensitive to leave a stale elevated session active even briefly.
