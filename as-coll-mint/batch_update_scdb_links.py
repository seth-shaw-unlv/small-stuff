#!/usr/bin/python

import csv
import sys

# Only works with MSS table. Update for each table.

TABLE = 'SPEC_MAN_MANUSCRIPTS_MAN'
ID = 'id_man'
IDENTIFIER = 'coll_man'
LINK = 'link_guide'

# SPEC_MAN_MANUSCRIPTS_MAN, id_man, coll_man, link_guide
# SPEC_ORAL_HISTORY_SOH, id_soh, coll_number_soh, link_digital_soh
# SPEC_PC_PHOTOCOLL_PHO, id_pho, coll_number_pho, link_guide_pho
# SPEC_UNLV_ARCHIVES_UAR, id_uar, link_guide_uar

# ArchivesSpace export
# export the query `select id, title, identifier, ead_location from resource where publish is True AND ead_location IS NOT Null;`
# Then search-replace the bracketed identifier form to the normal one.

if __name__ == '__main__':

    # Ensure we have the two arguments
    if not len(sys.argv) > 2:
        print 'Please provide both the archivesspace export (from db) and scdb export (from admin interface)'
        exit();

    # load up an identifier associative array storing arks for guides
    identifier_ark = {}
    with open(sys.argv[1]) as csvfile:
        reader = csv.DictReader(csvfile, delimiter='\t')
        for row in reader:
            identifier_ark[row['identifier']] = row['ead_location']

    # Run through the DB entries and create update statements
    update_sql = ''
    with open(sys.argv[2], 'rU') as csvfile:
        reader = csv.DictReader(csvfile, delimiter='|')
        for r in reader:
            if r['Link to Guide'].find('ark:') > -1:
		print(r['Coll #']+' already has an ark '+r['Link to Guide'])
                continue
            if r['Coll #'] in identifier_ark.keys():
                update_sql += "UPDATE {0} SET {1}='{2}' WHERE {3}='{4}';\n".format(TABLE, LINK, identifier_ark[r['Coll #']].strip(), ID, r['id'])
            else:
                print(r['Coll #']+' is not in ArchivesSpace')

    print(update_sql);
