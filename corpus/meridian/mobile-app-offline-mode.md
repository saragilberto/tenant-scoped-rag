---
title: "Using the Mobile App Without a Connection"
category: "Mobile"
version: "1.0"
visibility: empresa
---

The Meridian mobile app caches the last five hundred records you viewed, along with any tasks
assigned to you, so they remain visible when the device loses connectivity. Notes and task
completions made while offline are queued locally and synced automatically once the connection
returns, in the order they were created. Editing a record that has changed on the server since it
was cached is the one case handled with a conflict prompt rather than automatic merging: the app
shows both versions side by side and asks which one to keep. Searching for a record not already in
the local cache is unavailable offline, since search always queries the server directly rather than
the local cache.
