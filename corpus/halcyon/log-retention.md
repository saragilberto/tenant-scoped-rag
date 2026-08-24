---
title: "How Long Halcyon Retains Audit Logs"
category: "Account & Security"
version: "1.0"
visibility: restrito
---

## Retention period

Because Halcyon handles billing data, audit logs are retained for seven years by default, far longer
than typical account activity logs, to satisfy common financial record-keeping requirements.

## What is logged

Every invoice creation, refund, payment method change, and permission change is logged with the
acting member's identifier and a timestamp. Viewing a customer's billing history is also logged,
unlike in most Halcyon screens, because billing data views are considered sensitive enough to audit
on their own.

## Immutability

Audit log entries cannot be edited or deleted by any role, including the workspace owner, for the
full seven-year retention period. This is enforced at the storage layer rather than only in the
application, so a compromised admin account cannot tamper with the trail.

## Requesting an export

A full audit log export requires a written request through Halcyon support rather than a self-service
button, given the sensitivity and typical size of seven years of billing-related audit data.
