---
title: "Configuring SSO for Your Billing Workspace"
category: "Account & Security"
version: "1.2"
visibility: restrito
---

## Protocol support

Halcyon supports both SAML 2.0 and OpenID Connect for single sign-on, chosen per workspace at setup
time; a workspace cannot run both protocols simultaneously.

## Billing admin exception

Even with SSO enforced, the workspace owner keeps a password-based emergency login path specifically
for the billing admin role, since losing access to billing during an identity provider outage carries
real financial risk.

## Attribute mapping

Halcyon expects a role attribute in the SSO assertion to determine whether a newly provisioned member
becomes a billing admin, a finance viewer, or a standard member. Missing this attribute provisions the
member with the lowest-privilege standard role by default, never billing admin.

## Testing before enforcing

Halcyon strongly recommends testing SSO with a non-billing-admin account first, since enforcing SSO
workspace-wide before confirming the handshake works can lock out every member simultaneously if the
identity provider configuration has an error.
