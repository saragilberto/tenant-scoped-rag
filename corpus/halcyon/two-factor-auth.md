---
title: "Turning On Two-Factor Authentication"
category: "Account & Security"
version: "1.0"
visibility: empresa
---

## Setup

From account settings, choose "Security" then "Two-factor authentication" to display a QR code for
pairing with an authenticator app. Halcyon requires two-factor authentication on every account with
the billing admin role; it is optional for other roles unless the workspace owner enforces it
workspace-wide.

## Backup codes

Ten backup codes are generated at setup and can be regenerated at any time, which immediately
invalidates the previous set. Regenerating backup codes does not require re-entering a current
authenticator code, only the account password.

## Grace period for billing admins

A newly promoted billing admin has a seven-day grace period to configure two-factor authentication
before being locked out of billing actions, though non-billing actions remain available during the
grace period.

## Resetting a lost device

Losing both the authenticator device and the backup codes requires identity verification through
Halcyon support before two-factor authentication can be reset on the account, which can take up to
two business days.
