---
title: "Billing Customers in Multiple Currencies"
category: "Billing"
version: "1.0"
visibility: departamentos
---

## Setting a customer's currency

A customer's billing currency is set at creation and generally cannot be changed afterward, since
changing it would leave historical invoices in a currency inconsistent with the customer's ongoing
subscription.

## Plan pricing per currency

A plan can define a separate fixed price for each supported currency rather than relying on a live
exchange rate at invoice time, which keeps pricing predictable for the customer even if exchange
rates move significantly between invoices.

## Currencies without explicit pricing

If a plan has no explicit price defined for a customer's currency, that plan cannot be assigned to
the customer at all; Halcyon does not fall back to an automatic currency conversion for subscription
pricing.

## Reporting across currencies

Revenue reports show a converted total in the workspace's reporting currency alongside the original
amounts, using the exchange rate in effect on the invoice date, so historical reports do not shift
retroactively as rates change later.
