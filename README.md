**This repository is deprecated and will no longer be updated. I've moved the relevant parts to other repositories.**

New locations:

- EZID: [https://github.com/UNLV-Libraries/ezid](https://github.com/UNLV-Libraries/ezid)
- ArchivesSpace related: [https://github.com/UNLV-Libraries/ArchivesSpace-authority-project/tree/master/misc](https://github.com/UNLV-Libraries/ArchivesSpace-authority-project/tree/master/misc)
- Islandora derivatives script: [https://gist.github.com/seth-shaw-unlv/bd64930fa1f75be3aba05ade34433092](https://gist.github.com/seth-shaw-unlv/bd64930fa1f75be3aba05ade34433092)

# small-stuff
Small bits that aren't part of anything else.

## as-coll-mint

One script to batch mint EZIDs for resources in ArchivesSpace and another to generate SQL Update statements for the special collections online database.

## as-export-csv

Script to export Agents in a CSV via the API since the existing export is unusable.

## as-sql

Miscellaneous SQL queries to use with an ArchivesSpace database

## migrate-locations-as

Scripts used in exploring the option of moving from a locations management spreadsheet to the ArchivesSpace locations module.

## ead-numbered-components_to_tsv.xsl

An XSLT for creating a TSV file of container titles from an EAD with numbered components.

## cdm-mint

Script to mint ARKs for every item in a CONTENTdm collection. (Uses the Catcher Service.)

## cdm-update-as

Scripts to populate ArchivesSpace digital object instances based on CONTENTdm objects.

- cdm_update_as.py works by matching CDM object titles and a collection identifier to AS archival object titles and resource identifiers.
- cdm_update_as_pho.py works by taking an Image ID from a CDM object field and matching it to an AS archival object component ID. *Currently only produces a TSV file of matches and errors. Needs to be updated to use ARKs instead once ARKs are minted for these CDM objects.*
- csv_link_ref_id.py takes a CSV of ARKs, digital ids, titles, and ArchivesSpace ref_ids (usually from ead-numbered-components_to_tsv.xsl) to create digital object records in ArchivesSpace.

## ezid

Scripts for querying and updating EZID ARKs.

## islandora-8

One script, generate-image-service-files.php, for kicking off image derivatives after a large migration. 
