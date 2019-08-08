#! /usr/bin/python

import CDM
import os, sys, logging, csv
import json

if __name__ == '__main__':

    ws_url='https://server17304.contentdm.oclc.org'
    queryClient = CDM.QueryClient(ws_url)
    # Check arguments
    if len(sys.argv)<2:
        sys.exit("Please provide at least one CDM alias to query.")

    query='0' # get every item
#    fields = ['date','creato','covera','narrat']
#    fields = ['creato','indivi','contri','indiva']
#    fields = ['group','identa','groupa','groupb']
    fields = ['corpor','group','affili','identa']
    for alias in sys.argv[1:]:
        value_counts = {}
        for result in queryClient.query(alias,query,fields):

            for field in fields:
                # Nothing to see here?
                if (field not in result) or not result[field]:
                    continue

                # Have we seen this field yet?
                if not field in value_counts:
                    value_counts[field] = {}

                for value in result[field].split(';'):
                    value = value.strip()

                    # A blank got through, skip it.
                    if not value:
                        continue

                    # Have we seen this value in this field yet?
                    if not value in value_counts[field]:
                        value_counts[field][value] = 0;

                    # Tally
                    value_counts[field][value] += 1

        for field, value_count in value_counts.items():
            for value, count in value_count.items():
                print("\t".join((alias,field,value,str(count))))
