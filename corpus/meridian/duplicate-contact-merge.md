---
title: "Merging Duplicate Contacts"
category: "Data Import"
version: "1.2"
visibility: empresa
---

Meridian flags likely duplicate contacts nightly based on matching full name and company, surfacing
them in a review queue rather than merging automatically. From the review queue, choosing "Merge"
opens a side-by-side comparison where the reviewer picks which record's values win for each
conflicting field, while non-conflicting fields are combined automatically. All activity history,
notes, and associated deals from both records move to the surviving record, and the merged-away
record's old ID redirects to the surviving one for at least ninety days, so old bookmarks and
integration references do not immediately break. A merge cannot be undone once confirmed, which is
why the comparison screen requires an explicit confirmation step rather than merging as soon as
"Merge" is clicked.
