---
title: "Connecting Your Inbox for Email Sync"
category: "Integrations"
version: "1.0"
visibility: empresa
---

## What sync does

Once an inbox is connected, messages sent to or received from a known contact are automatically
logged on that contact's timeline, without any manual forwarding or BCC step required from the sales
rep.

## Connecting an account

From the personal settings screen, choose "Connect inbox" and authorize access through your email
provider's own consent screen. Meridian never stores your mailbox password directly; it holds only
the access token issued by the provider, which can be revoked at any time from the provider's own
security settings.

## What gets excluded

Sync excludes any thread where none of the participants match a known contact or lead, and it
excludes internal messages between two addresses on the same company domain as the workspace owner,
to avoid logging internal chatter as customer communication.

## Disconnecting

Disconnecting an inbox stops future sync immediately but does not remove messages already logged on
contact timelines. Removing that history requires a separate bulk-delete action from the contact
activity settings.
