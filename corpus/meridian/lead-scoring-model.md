---
title: "Understanding the Lead Scoring Model"
category: "Reporting"
version: "2.0"
visibility: restrito
---

## Score components

Each lead's score combines firmographic fit (company size, industry) and engagement signals (email
opens, page visits, form submissions), weighted separately and summed into a single number between
zero and one hundred.

## Recalculation timing

Scores recalculate whenever a new engagement signal arrives, not on a fixed schedule, so a lead's
score can change several times within the same day if it is actively browsing or opening emails.

## Threshold for sales handoff

Leads crossing a score of seventy are automatically routed to the sales queue defined by the
territory rules, regardless of whether marketing had already qualified them manually. This threshold
is configurable per workspace but changing it does not retroactively re-route leads already below
the old threshold.

## Score decay

A lead's engagement component decays gradually if there is no new activity for thirty days, reducing
the total score even without any negative signal, to reflect declining interest over time.
