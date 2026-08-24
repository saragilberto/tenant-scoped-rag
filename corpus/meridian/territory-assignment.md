---
title: "Setting Up Territory-Based Lead Assignment"
category: "Configuration"
version: "1.0"
visibility: departamentos
---

## Defining a territory

A territory is a named rule set matching on company country, company size band, or a custom field,
evaluated in the order the territories are listed. The first matching territory claims the lead, so
more specific territories should be listed above broader catch-all ones.

## Assignment within a territory

Once a territory matches, the lead is assigned using that territory's own rotation: either round
robin across its members or weighted by each member's current open lead count. Weighted rotation
recalculates on every new lead rather than on a fixed schedule.

## Unmatched leads

A lead matching no territory falls into the default unassigned queue, visible to sales managers, who
can assign it manually or adjust the territory rules so similar future leads match automatically.
