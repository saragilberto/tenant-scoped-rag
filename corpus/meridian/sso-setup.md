---
title: "Setting Up Single Sign-On (SSO) for Your Organization"
category: "Account & Security"
version: "1.4"
visibility: restrito
---

## Supported protocol

Meridian supports SAML 2.0 for single sign-on. The workspace owner uploads the identity provider's
metadata file from the SSO settings screen, and Meridian generates a service provider metadata file
in return for the identity provider's configuration.

## Just-in-time provisioning

When SSO is enabled, members who authenticate successfully but do not yet have a Meridian account are
provisioned automatically on first sign-in, using the name and role attributes sent in the SAML
assertion. Provisioning can be restricted to specific email domains from the advanced SSO settings.

## Enforcing SSO only

Once SSO is confirmed working for at least one test member, the workspace owner can disable
password-based sign-in entirely. This is a one-way switch for regular members — only workspace
owners retain a password fallback, specifically to avoid a full lockout if the identity provider
becomes unreachable.

## Debugging a failed handshake

Most SSO handshake failures trace back to a clock skew between Meridian and the identity provider, or
to an assertion missing a required attribute. The SSO settings screen shows the last three failed
handshake attempts with the specific validation error for each.
