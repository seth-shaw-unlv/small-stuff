#! /usr/bin/python

import os, sys, logging, csv
import json

# Python 3

if __name__ == '__main__':
    
    if len(sys.argv)<2:
        sys.exit("Please provide CSV of catcher updates.")
    logging.basicConfig(format='%(levelname)s - %(message)s',
                        level=logging.INFO)

    base_path = sys.argv[1]
    logging.debug('TemaTres Export base path set to "%s"' % (base_path))

    terms = {}

    # prefTerms
    with open(os.path.join(base_path, 'prefTerms.csv'), 'rU') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';', dialect=csv.excel)
        for row in reader:
            # print("ID: %s\tTerm: %s" % (row['id'], row['term']))
            logging.debug("ID: %s\tTerm: %s" % (row['id'], row['term']))
            terms[row['id']] = {'name':row['term']}
    # relTerms
    # uri
    # altTerms
    # notes
    
    print(json.dumps(terms, sort_keys=True, indent=2))