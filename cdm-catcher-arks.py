#! /usr/bin/python

import CDM
import sys
import json
import csv

if __name__ == '__main__':

    alias='p17304coll4'
    username='seth.shaw@unlv.edu'
    password='YUsPhXqe'
    license='6WNYM-LH5KC-RJZMY-HZN65'
    field_to_update = 'object'
    catcher_url='http://server17304.contentdm.oclc.org:8888/'
    catcher = CDM.CatcherSession(catcher_url,username,password,license)
    if not catcher.checkLogin():
        sys.exit("Could not connect to the catcher service.\n")
    with open(sys.argv[1], 'rU') as csvfile: #'rU' because Mac Excel exports are wierd

        # reader = csv.DictReader(csvfile, delimiter='\t')
        reader = csv.reader(csvfile, delimiter='\t')
        for row in reader:
            # print json.dumps(row)
            # (alias, id, pointer) = row['cdm_id'].strip().split('/')
            alias = row[0]
            pointer = row[1]
            # Update CDM and report
            value = row[2]
            catcher.edit(alias, pointer, field_to_update, value)
            print("\t".join((alias,pointer,value,json.dumps(catcher.transactions[-1]))))
            # print("\t".join((alias,pointer,field_to_update,value)))
