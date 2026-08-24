---
title: "Sending Bulk Email Campaigns to Contact Lists"
category: "Marketing"
version: "1.2"
visibility: empresa
---

## Building the recipient list

A campaign's recipient list is built from a saved contact filter, evaluated fresh at send time rather
than when the campaign was drafted, so contacts added after drafting but before sending are still
included if they match the filter.

## Suppression rules

Contacts who unsubscribed from any previous campaign are automatically excluded from every future
campaign's recipient list, and this exclusion cannot be overridden per campaign — it applies
workspace-wide once a contact unsubscribes.

## Send throttling

Campaigns larger than ten thousand recipients are sent in batches over several hours rather than all
at once, to stay within the sending reputation limits of the underlying delivery provider. The
campaign report shows delivery progress as the batches complete.

## Reply handling

Replies to a campaign message are routed to the campaign owner's connected inbox if email sync is
enabled for them, and logged on the replying contact's timeline the same way a normal synced email
would be.
