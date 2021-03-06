#!/usr/bin/python

import base64
import ConfigParser
import json
import logging
import argparse, sys, csv
import urllib, urllib2

"""
Create Links to CONTENTdm digital objects in ArchivesSpace (CSV source)

Assuming the CONTENTdm digital object's title is the same as an Archival Object
in ArchivesSpace, we can create a Digital Object in ArchivesSpace with either
the CONTENTdm URI or an ARK and link it to the Archival Object.

@author Seth Shaw
@date 2018-05-29

"""

class ASClient(object):
    """An ArchivesSpace Client"""

    SESSION = ''

    def __init__(self, api_root, username, password):
        self.api_root = api_root
        self.login(username, password)

    def api_call(self, path, method = 'GET', data = {}, as_obj = True):

        path = self.api_root + path

        # urllib2 will force a call to POST if the data element is provided.
        # So, a query string must be appended to path if you want a GET
        if method == 'GET':
            if data:
                request = urllib2.Request(path + '?' + urllib.urlencode(data))
            else:
                request = urllib2.Request(path)
        elif method == 'POST':
            if isinstance(data, dict):
                data = json.dumps(data)
            request = urllib2.Request(path, data)
        else:
            logging.error("Unknown or unused HTTP method: %s" % method)
            return

        if self.SESSION: #only absent during login.
            request.add_header("X-ArchivesSpace-Session",self.SESSION)

        logging.debug("ArchivesSpace API call (%s;%s): %s %s %s %s" % (path, json.dumps(data), json.dumps(request.header_items()), request.get_method(), request.get_full_url(), request.get_data()) )
        try:
            response = urllib2.urlopen(request)
        except urllib2.HTTPError as h:
            logging.error("Unable to process ArchivesSpace API call (%s): %s - %s - %s" % (path, h.code, h.reason, h.read()))
            return {}
        if as_obj:
            return json.load(response); #object
        else:
            return response #readable stream

    def api_call_paginated(self, path, method = 'GET', data = {}):
        objects = [] #The stuff we are giving back
        data['page'] = 1
        last_page = 1 #assume one page until told otherwise
        data['page_size'] = 200

        while data['page'] <= last_page:

            #The call
            archival_objs = self.api_call(path, method, data)

            #Debuggging and Pagination
            logging.debug("Page %s of %s" % (data['page'], last_page))
            # logging.debug(json.dumps(archival_objs))
            if archival_objs['last_page'] != last_page:
                logging.debug('Updating last page from %s to %s' % (last_page, archival_objs['last_page']))
                last_page = archival_objs['last_page']

            objects += archival_objs['results']

            #Next, please....
            data['page'] += 1

        return objects

    def login(self, username, password):
        path = '/users/%s/login' % (username)
        obj = self.api_call(path,'POST', urllib.urlencode({'password': password }))
        self.SESSION = obj["session"]

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("csv", help="a CSV of CONTENTdm records")
    parser.add_argument("-f","--collection-id-field", help='the CONTENTdm field storing the source collection\'s identifier (overrides config.ini)')
    parser.add_argument("-k","--ark-field", help='the CONTENTdm field to use for the object ARKs (overrides config.ini)')
    parser.add_argument("-o","--digital-object-field", help='the CONTENTdm field to use for the digital object\'s identifier (overrides config.ini)')
    parser.add_argument("-r","--date-range-field", help='the CONTENTdm field storing digital object date ranges')
    parser.add_argument("-s","--date-single-field", help='the CONTENTdm field storing digital object single dates')
    parser.add_argument("-v","--verbosity", help="change output verbosity: DEBUG, INFO (default), ERROR")
    parser.add_argument("-d","--dry", help="doesn't update ArchivesSpace, used for testing", action="store_true")
    args = parser.parse_args()

    dry = False
    if args.dry:
        dry = True

    # Configuration
    verbosity = logging.INFO
    if args.verbosity:
        if args.verbosity == 'DEBUG':
            verbosity = logging.DEBUG
        if args.verbosity == 'INFO': # Redundant, I know, but it keeps the list clean
            verbosity = logging.INFO
        if args.verbosity == 'ERROR':
            verbosity = logging.ERROR
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                        level=verbosity)

    global config
    config = ConfigParser.ConfigParser()
    configFilePath = r'config.ini'
    config.read(configFilePath)

    # Fields for CDM to return.
    # Will add the ark field, if used, and the collection id field later
    cdm_fields = ['title']

    # Which field holds the ARK?
    ark_field = None
    if config.get('cdm','ark-field'):
        ark_field = config.get('cdm','ark-field')
    if args.ark_field:
        ark_field = args.ark_field
    if ark_field:
        cdm_fields.append(ark_field)

    # Which field holds the Collection Identifier?
    cid_field = config.get('cdm','collid-field')
    if args.collection_id_field:
        cid_field = args.collection_id_field
    cdm_fields.append(cid_field)

    # Which field holds the Digital Object Identifier?
    do_field = config.get('cdm','doid-field')
    if args.digital_object_field:
        do_field = args.digital_object_field
    cdm_fields.append(do_field)

    # Which field holds the Digital Object Date Range?
    dr_field = config.get('cdm','date-range-field')
    if args.date_range_field:
        dr_field = args.date_range_field
    cdm_fields.append(dr_field)

    # Which field holds the Digital Object Signle Date?
    ds_field = config.get('cdm','date-single-field')
    if args.date_single_field:
        ds_field = args.date_single_field
    cdm_fields.append(ds_field)

    # Initialize AS client
    aspace_client = ASClient(config.get('archivesspace','api-prefix'),
                             config.get('archivesspace','username'),
                             config.get('archivesspace','password'))
    repository = config.get('archivesspace','repository')

    with open(args.csv, 'rU') as csvfile: #'rU' because Mac Excel exports are wierd
        current_as_rid = None
        current_cid = None
        reader = csv.DictReader(csvfile, dialect=csv.excel)
        for row in reader:

            # REPORT abd SKIP if the do has no identifier
            if not do_field in row:
                logging.warn('SKIPPING: no identifier ID for %s' % (json.dumps(row)))
                continue

            # Check for a change in the Collection ID and update AS resource id if needed
            if ((current_cid != row[cid_field]) or (current_as_rid == None)) and row[cid_field] :
                current_cid = row[cid_field]
                #Advanced queries don't work well with URL Encode, so we do it manually and attach it to the path ourselves.
                resource_query = '{"query":{"op":"AND","subqueries":[{"field":"identifier","value":"%s","jsonmodel_type":"field_query","negated":false,"literal":true},{"field":"primary_type","value":"resource","jsonmodel_type":"boolean_field_query"}],"jsonmodel_type":"boolean_query"},"jsonmodel_type":"advanced_query"}' % (urllib.quote_plus(current_cid))
                resources = aspace_client.api_call('/repositories/%s/search?page=1&aq=%s' % (repository,resource_query))
                #Sometimes we get bad identifiers from CDM, make sure what we get it good, or report back.
                if not resources['results']:
                    logging.warn('SKIPPING: Collection ID %s not found in ArchivesSpace for %s' % (row[cid_field],row[do_field]))
                    current_as_rid = None
                    continue
                # Take the first result uri
                current_as_rid = resources['results'][0]['uri']
                logging.debug('NEW Current AS Resource ID %s:%s' % (current_cid,current_as_rid))

            # REPORT and SKIP if the do has no ARK
            if ark_field and not row[ark_field]:
                logging.warn('SKIPPING: no ARK for %s/id/%d (%s:%s)' % (row['collection'],row['pointer'],current_cid,current_as_rid))
                continue
            title = row['title'].replace('&#x27;', "'").replace('&quot;','"')
            #  REPORT and SKIP if the do has no title
            if not 'title' in row:
                logging.warn('SKIPPING: no Title for %s/id/%d' % (row['collection'],row['pointer']))
                continue
            #  REPORT and SKIP if the do has no collection identifier
            if not cid_field in row:
                logging.warn('SKIPPING: no Collection ID (%s) for %s/id/%d' % (cid_field,row['collection'],row['pointer']))
                continue

            # For CDM date for matching and AS DO creation
            cdm_obj_date = ''
            as_do_date_obj = {}
            if ds_field in row and row[ds_field]:
                cdm_obj_date = row[ds_field]
                if not 'undated' in cdm_obj_date:
                    if '~' in cdm_obj_date:
                        as_do_date_obj['certainty'] = 'approximate'
                        cdm_obj_date = cdm_obj_date.strip('~')
                    as_do_date_obj['date_type'] = 'single'
                    as_do_date_obj['begin'] = cdm_obj_date
            elif dr_field in row and row[dr_field]:
                date_range_array = row[dr_field].split('; ')
                cdm_obj_date = '%s-%s' % (date_range_array[0],date_range_array[-1])
                as_do_date_obj['date_type'] = 'inclusive'
                as_do_date_obj['begin'] = date_range_array[0]
                as_do_date_obj['end'] = date_range_array[-1]

            # CREATE the AS Digital Object
            as_do = {'title':title,
                     'digital_object_id':row[do_field],
                     'publish':True,
                     'file_versions':[{'file_uri':row[ark_field],
                                       'publish':True,
                                       'is_representative':True}],
                     'dates':[]}

            if as_do_date_obj:
                as_do_date_obj['label'] = 'creation'
                as_do['dates'].append(as_do_date_obj)

            as_do_query = '{"query":{"op":"AND","subqueries":[{"field":"digital_object_id","value":"%s","jsonmodel_type":"field_query","negated":false,"literal":true},{"field":"primary_type","value":"digital_object","jsonmodel_type":"boolean_field_query"}],"jsonmodel_type":"boolean_query"},"jsonmodel_type":"advanced_query"}' % (urllib.quote_plus(row[do_field].replace('\n', '').replace('\r', '')))
            as_do_response = aspace_client.api_call('/repositories/%s/search?page=1&aq=%s' % (repository,as_do_query))

            as_do_uri = ''
            if as_do_response['total_hits'] == 0:
                # Make a new AS DO
                as_do_uri = 'FAKE/URI' # Incase the DRY option is enabled
                if dry:
                    logging.info('DRY: Would create AS digital object: %s' % (json.dumps(as_do)))
                else:
                    as_do_response = aspace_client.api_call('/repositories/%s/digital_objects' % (repository),'POST', as_do)
                    if not 'uri' in as_do_response:
                        logging.warn('FAILED to create AS digital object %s %s: %s' % ('/repositories/%s/digital_objects' % (repository), as_do, json.dumps(as_do_response)))
                        continue
                    as_do_uri = as_do_response['uri']
            else:
                as_do_uri = as_do_response['results'][0]['uri']
                logging.debug('FOUND: AS DO for %s: %s' % (row[do_field],as_do_uri))

            # Query ArchivesSpace for archival objects (ao) with matching title and collection URI (root record)
            ao_query = '{"query":{"op":"AND","subqueries":[{"field":"title","value":"%s","jsonmodel_type":"field_query","negated":false,"literal":true},{"field":"primary_type","value":"archival_object","jsonmodel_type":"boolean_field_query"}],"jsonmodel_type":"boolean_query"},"jsonmodel_type":"advanced_query"}' % (urllib.quote_plus(title.replace('"','\\"').replace('\n', '').replace('\r', '')))
            archival_objects = aspace_client.api_call('/repositories/%s/search?page=1&aq=%s&root_record=%s' % (repository,ao_query,current_as_rid))

            if not archival_objects['results']:
                logging.warn ('SKIPPING: Could not find title "%s" in resource %s for %s (%s)' % (title,current_as_rid,row[do_field],as_do_uri))
                continue
            # Check to see if we have different URIs, or multiple of the same
            ao_objs = list()
            for ao in archival_objects['results']:
                ao_obj = json.loads(ao['json'])
                # Have we seen this object in the results before?
                found_existing_uri = False
                for existing_ao in ao_objs:
                    if existing_ao['uri'] == ao_obj['uri']:
                        found_existing_uri = True
                        continue
                if not found_existing_uri:
                    ao_objs.append(ao_obj)

            if len(ao_objs) > 1:
                # Check to see if we get a date match
                logging.debug('CHECKING DATES for %s (%s)'%(row[do_field],cdm_obj_date))
                date_matches = []
                for ao in ao_objs:
                    for ao_date in ao['dates']:
                        ao_date_expression = ao_date['expression']
                        # AS has some decade expressions that don't play nice (e.g. 1950s and 1950s-1960s)
                        if 's' in ao_date_expression: #decade expression
                            date_parts = ao_date_expression.split('-')
                            if len(date_parts) > 1: # decade range
                                first_decade = date_parts[0].strip('s')
                                second_decade = date_parts[1]
                                if second_decade.endswith('s'):
                                    second_decade = '%s9' % (second_decade.strip('s')[:-1])
                                ao_date_expression = '-'.join((first_decade,second_decade))
                            else: #single decade
                                decade = ao_date_expression.strip('0s')
                                ao_date_expression = '%s0-%s9' % (decade,decade)
                        if cdm_obj_date == ao_date_expression :
                            date_matches.append(ao)
                            continue

                if len(date_matches) > 1:
                    result_uris = []
                    for ao in date_matches:
                        result_uris.append(ao['uri'])
                    logging.warn('SKIPPING: multiple Archival Objects with title "%s" and matching dates (%s) in resource %s for %s (%s): %s'% (title,cdm_obj_date,current_as_rid,row[do_field],as_do_uri,','.join(result_uris)))
                    continue
                elif len(date_matches) < 1:
                    result_uris = []
                    for ao in ao_objs:
                        result_uris.append(ao['uri'])
                    logging.warn('SKIPPING: multiple Archival Objects with title "%s" in resource %s for %s (none of the dates match "%s"): %s'% (title,current_as_rid,row[do_field],cdm_obj_date,','.join(result_uris)))
                    continue
                elif len(date_matches) == 1: # Only one matches title and date, reset the result list to match
                    ao_objs = date_matches

            # Get a cleaner object reference to use
            as_ao = ao_objs[0]
            logging.debug('MATCH: Archival Object "%s" (%s) matches CDM "%s" date: %s (%s)' % (as_ao['display_string'].replace('\n', '').replace('\r', ''),as_ao['uri'],title,cdm_obj_date,row[do_field]))

            # If the AS AO already has a DO, we assume it is the same match we just identified.
            has_do = False
            for instance in as_ao['instances']:
                if not instance['instance_type'] == 'digital_object':
                    continue
                if  instance['digital_object']['ref'] == as_do_uri:
                    has_do = True
                    continue
            if has_do:
                logging.info('SKIPPING: Archival Object %s already linked to %s'% (as_ao['uri'],as_do_uri))
                continue

            # Update ao in AS with instance link using the ARK
            # based on https://github.com/djpillen/bentley_scripts/blob/master/update_archival_object.py
            # Update the Archival Object
            as_do_instance = {'instance_type':'digital_object','digital_object':{'ref':as_do_uri}}
            as_ao['instances'].append(as_do_instance)
            if dry:
                logging.info('DRY: Would update AS Archival Object %s with new instance %s' % (as_ao['uri'], as_do_instance))
            else:
                ao_update_response = aspace_client.api_call(as_ao['uri'],'POST', as_ao)
                if 'status' in ao_update_response:
                    logging.info('%s: AS Archival Object %s with AS Digital Object %s for CDM object %s : %s' % (ao_update_response['status'],ao_update_response['id'],as_do_uri,row[do_field],title))
                else:
                    logging.info('Unable to update AS Archival Object %s with AS Digital Object %s for CDM object %s : %s' % (as_ao['uri'],as_do_uri,row[do_field],title))
