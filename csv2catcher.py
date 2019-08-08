#! /usr/bin/python

import CDM
import os, sys, logging, csv
import json

if __name__ == '__main__':

    alias='p17304coll4'
    username='seth.shaw@unlv.edu'
    password='YUsPhXqe'
    license='6WNYM-LH5KC-RJZMY-HZN65'
    catcher_url='http://server17304.contentdm.oclc.org:8888/'
    catcher = CDM.CatcherSession(catcher_url,username,password,license)
    if not catcher.checkLogin():
        sys.exit("Could not connect to the catcher service.\n")

    # Check arguments
    if len(sys.argv)<2:
        sys.exit("Please provide CSV of catcher updates.")
    if os.path.isfile(sys.argv[1]) != True :
        sys.exit('"'+sys.argv[1] + '" is not a file. Please provide the CSV of catcher updates.')

    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

    with open(sys.argv[1], 'rU') as csvfile: #'rU' because Mac Excel exports are wierd

        reader = csv.DictReader(csvfile, dialect=csv.excel)
        for row in reader:
            # Sanity checks
            if not 'alias' in row.keys() or not row['alias']:
                logging.warning("Alias for this row not found")
                continue
            elif not 'pointer' in row.keys() or not row['pointer']:
                logging.warning("Pointer for this row not found")
                continue
            elif not 'field' in row.keys() or not row['field']:
                logging.warning("No field to update for %s/%s" % (row['alias'],row['pointer']))
                continue
            elif not 'value' in row.keys() or not row['value']:
                logging.warning("No value to update for field %s in %s/%s" % (row['field'],row['alias'],row['pointer']))
                continue

            # Update CDM and report
            catcher.edit(row['alias'], row['pointer'], row['field'], row['value'])
            print("\t".join((row['alias'], row['pointer'], row['field'], row['value'],json.dumps(catcher.transactions[-1]))))
