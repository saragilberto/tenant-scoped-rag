---
title: "Configuring Role-Based Permissions"
category: "Account & Security"
version: "1.6"
visibility: restrito
---

## Built-in roles

Meridian ships with four built-in roles: Owner, Manager, Sales Rep, and Read Only. Built-in roles
cannot be edited, but any of them can be cloned into a custom role that starts with the same
permissions and can then be adjusted freely.

## Permission scope

Each permission has a scope of "own records", "team records", or "all records", set independently
for view, edit, and delete actions. A Sales Rep can typically edit only their own deals while a
Manager edits their team's deals, using the same underlying permission with a different scope.

## Role changes take effect immediately

Changing a member's role applies immediately to their active session, without requiring them to sign
out and back in, which is a deliberate choice for revoking access quickly when someone changes teams
or leaves the organization.
