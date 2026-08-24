---
title: "Adding Custom Fields to Contacts and Deals"
category: "Configuration"
version: "1.3"
visibility: departamentos
---

## Field types

Meridian supports text, number, date, single-select, and multi-select custom fields on contacts,
companies, and deals. Single-select fields can later be converted to multi-select without data loss,
but the reverse conversion drops any record that had more than one value selected.

## Required fields

A custom field can be marked required, but only for records created after the requirement is added.
Existing records missing the field are flagged in a "data completeness" filter rather than being
blocked from being saved again.

## Field-level permissions

Custom fields can be restricted to specific roles, hiding both the field and its value from members
without that role rather than just making it read-only. This is commonly used for fields holding
internal deal scoring that should not be visible to junior sales roles.
