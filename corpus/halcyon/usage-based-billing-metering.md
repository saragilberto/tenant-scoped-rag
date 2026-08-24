---
title: "Setting Up Usage-Based Billing Metering"
category: "Billing"
version: "1.1"
visibility: departamentos
---

## Reporting usage

Usage events are reported to Halcyon through the metering API, each tagged with a customer
identifier, a metric name, and a quantity. Events are aggregated per billing period rather than
billed individually as they arrive.

## Aggregation methods

Each metric is configured to aggregate by sum, maximum, or last-value over the billing period.
Sum is typical for consumption-style metrics like API calls, while maximum suits metrics like peak
concurrent seats where billing the highest point observed makes more sense than the total.

## Late-arriving events

An event reported after its billing period has already been invoiced is applied to the following
period's invoice rather than reopening the already-issued invoice, to keep issued invoices immutable.

## Duplicate event protection

Each usage event can include an idempotency key; submitting the same key twice is counted once,
which protects against double-billing when a client retries a metering call after a network timeout.
