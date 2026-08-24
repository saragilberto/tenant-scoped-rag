---
title: "Configuring Dunning for Failed Payments"
category: "Billing"
version: "1.5"
visibility: restrito
---

## What dunning does

When a subscription payment fails, Halcyon's dunning process retries the charge automatically on a
schedule rather than canceling the subscription immediately, giving the customer time to update their
payment method.

## Default retry schedule

The default schedule retries at 1 day, 3 days, and 7 days after the initial failure. If all three
retries fail, the subscription is marked past due and, after an additional grace period of 7 days,
automatically canceled unless dunning settings specify otherwise.

## Customer notifications

Each retry attempt, successful or not, triggers an email to the customer's billing contact. These
notifications cannot be disabled individually, only by disabling the entire dunning workflow for a
plan, which is generally discouraged since it removes the customer's warning before cancellation.

## Manual intervention

A billing admin can pause dunning for a specific subscription, halting further automatic retries
while the admin follows up with the customer directly, then resume the normal schedule from wherever
it left off.
