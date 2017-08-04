#!/usr/bin/python

import csv
import sys

if __name__ == '__main__':

    # Ensure we have the two arguments
    if not len(sys.argv) > 2:
        print 'Please provide both the archivesspace export and scdb export'
        exit();

    # load up an identifier associative array storing arks for guides
    identifier_ark = {}
    with open(sys.argv[1]) as csvfile:
        reader = csv.DictReader(csvfile, delimiter='\t')
        for row in reader:
            identifier_ark[row['identifier']] = row['ead_location']

    # Run through the DB entries and create update statements
    update_sql = ''
    with open(sys.argv[2]) as csvfile:
        reader = csv.DictReader(csvfile, delimiter='\t')
        for r in reader:
            if r['coll_man'] in identifier_ark.keys():
                update_sql += "UPDATE SPEC_MAN_MANUSCRIPTS_MAN SET link_guide='{0}' WHERE id_man='{1}'\n".format(identifier_ark[r['coll_man']],r['id_man'])
            else:
                print(r['coll_man']+' is not in ArchivesSpace')

    print(update_sql);
