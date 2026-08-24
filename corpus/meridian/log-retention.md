---
title: "Audit Log Retention Policy in Meridian"
category: "Account & Security"
version: "1.0"
visibility: restrito
---

## What gets logged

Meridian records an audit entry for every sign-in, permission change, data export, and record
deletion. Read-only actions such as viewing a contact are not logged, to keep the audit trail focused
on actions that change state or move data out of the workspace.

## Retention window

Audit log entries are retained for 400 days on the standard plan. After that window, entries are
permanently deleted on a rolling basis and cannot be recovered, including by Meridian support staff.

## Exporting before expiry

Workspace owners can export the full audit log as a CSV file at any time from the security screen.
Organizations with compliance requirements longer than 400 days are expected to run this export
periodically rather than relying on Meridian to extend retention.

## Who can access the log

Only workspace owners and members with the "security auditor" role can view the audit log. This role
grants read-only access to the log and nothing else — it does not carry any of the other
administrative permissions that workspace owners have.
