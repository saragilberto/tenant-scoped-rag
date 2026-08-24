---
title: "Customizing Pipeline Stages"
category: "Pipeline"
version: "2.0"
visibility: departamentos
---

## Default stages

Every new pipeline starts with five stages: New, Qualified, Proposal, Negotiation, and Closed. These
can be renamed freely, but the first and last stages cannot be deleted, since they anchor the
"time in pipeline" and "win rate" reports.

## Adding a stage

A workspace owner can insert a stage anywhere between the first and last by dragging the stage
divider in the pipeline settings screen. Existing deals are not moved automatically when a stage is
inserted; only new deals created after the change will pass through it by default.

## Stage automation

Each stage can trigger an automation when a deal enters it, such as assigning a task to the deal
owner or posting a message to a connected chat channel. Automations run once per entry into a stage,
so a deal that moves backward and forward across the same stage boundary triggers the automation
again each time.
