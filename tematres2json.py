#! /usr/bin/python

import os, sys, errno, logging, csv
import json

# Python 3

if __name__ == '__main__':
    
    if len(sys.argv)<2:
        sys.exit("Please provide CSV of catcher updates.")
    logging.basicConfig(format='%(levelname)s - %(message)s',
                        level=logging.INFO)

    base_path = sys.argv[1]
    logging.debug('TemaTres Export base path set to "%s"' % (base_path))

    note_types = {
        'OMI': 'collection_id',
        'RS': 'resource',
        'AL': 'alt_names',
        'BN': 'description',
        'FA': 'finding_aid',
        'RN': 'relationships',
        'SV': 'standard_vocabulary',
        'URI': 'uri',
        'NC': 'catalogers_note',
        'NP': 'private',
        'JHP': 'jhp_link',
        'NA': 'scope',
        'NB': 'bibliographic',
        'NH': 'history',
        '': 'other',
    }
    
    non_preferred_term_map = {
        '': 'non_preferred',
        'Abbreviation' : 'abbr',
        'Full form of the term': 'fuller',
        'Spelling variant': 'spelling',
    }

    terms = {}

    # prefTerms
    with open(os.path.join(base_path, 'prefTerms.csv'), 'rU') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';', dialect=csv.excel)
        for row in reader:
            # print("ID: %s\tTerm: %s" % (row['id'], row['term']))
            logging.debug("ID: %s\tTerm: %s" % (row['id'], row['term']))
            terms[row['id']] = {'name':row['term']}
    # relTerms
    with open(os.path.join(base_path, 'relTerms.csv'), 'rU') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';', dialect=csv.excel)
        for row in reader:
            terms[row['rt_internal_term_id']].setdefault('rels', []).append({'rel_type': row['sub_type'], 'target': row['internal_term_id']})
    # uri
    with open(os.path.join(base_path, 'uris.csv'), 'rU') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';', dialect=csv.excel)
        for row in reader:
            if (row['tema_id'] in terms.keys() and row['uri_type_id'] == '34'):
                terms[row['tema_id']].setdefault('exact_match', []).append(row['uri'])
    # altTerms
    with open(os.path.join(base_path, 'altTerms.csv'), 'rU') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';', dialect=csv.excel)
        for row in reader:
            term_type = non_preferred_term_map[row['sub_type']]
            terms[row['internal_term_id']].setdefault('alt_terms', []).append({'term_type': term_type, 'term': row['uf_term']})
    # notes
    with open(os.path.join(base_path, 'notes.csv'), 'rU') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';', dialect=csv.excel)
        for row in reader:
            if (row['id_tema'] in terms.keys()):
                terms[row['id_tema']].setdefault(note_types[row['tipo_nota']], []).append(row['nota'])
    try:
        print(json.dumps(terms, sort_keys=True, indent=2, ensure_ascii=False).encode('utf8').decode())
    except IOError as e:
        if e.errno == errno.EPIPE:
            pass # Do nothing; a pipe disconnect is okay here.