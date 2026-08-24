---
title: "Setting Up Tax Calculation"
category: "Billing"
version: "1.2"
visibility: departamentos
---

## Automatic tax by default

Halcyon calculates tax automatically based on the customer's registered billing address and the
product's configured tax category, using rates that update automatically as regulations change in
supported regions.

## Tax exemption

A customer can be marked tax-exempt with a certificate reference stored on their record. Exempt
customers are shown a zero tax line on invoices rather than the line being omitted entirely, so the
exemption is visible for audit purposes rather than silently invisible.

## Unsupported regions

For regions without built-in automatic tax support, tax must be configured manually as a fixed
percentage per product, and Halcyon will not attempt to guess a rate or apply automatic updates for
that region.

## Tax on metered usage

Metered usage line items are taxed using the rate in effect at the end of the billing period in which
the usage occurred, not the rate at the time each individual usage event was recorded.
