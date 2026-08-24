---
title: "Importing Contacts and Leads via CSV"
category: "Data Import"
version: "2.0"
visibility: empresa
---

## Preparing the file

Meridian accepts UTF-8 encoded CSV files up to 50,000 rows per upload. The first row must contain
column headers, and at minimum one column must map to either "Full Name" or both "First Name" and
"Last Name" — imports without a name mapping are rejected before any row is processed.

## Field mapping

After upload, Meridian shows a mapping screen that guesses column purposes from the header text.
Columns that cannot be guessed are left as "Do not import" by default, so review the mapping screen
carefully rather than accepting the guesses blindly.

## Duplicate handling

During import, a row is treated as a duplicate of an existing contact when the company name and the
full name match exactly, case-insensitive. Duplicates are merged by default, keeping the existing
record's owner and adding any new field values from the imported row. This behavior can be switched
to "skip duplicates" from the advanced import options.

## Failure reporting

Rows that fail validation (missing required fields, malformed dates) do not stop the import. They
are collected into a downloadable error report at the end of the run, with the original row number
and the reason for the failure, so the source file can be corrected and re-uploaded for just those
rows.
