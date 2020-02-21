#!/usr/bin/python

import base64
import ConfigParser
import json
import logging
import argparse, sys, csv
import urllib, urllib2

"""
Batch Add Classifications (TSV source)

Not fully automated...
First use SQL to find resources to update:
```
SELECT
         REPLACE(REPLACE(REPLACE(resource.identifier, '","','-'),'["',''),'",null,null]','') AS identifier,
         resource.title,
         resource.id
FROM resource 
LEFT JOIN classification_rlshp ON resource.id = classification_rlshp.resource_id 
WHERE resource.publish is TRUE
AND classification_rlshp.classification_id is NULL
ORDER BY resource.identifier
```
Then add a classification_uri column with the appropriate classification URI 
for each row. Use that TSV as the script source.

Note: suppressed records cannot be updated and will return a warning.

@author Seth Shaw
@date 2020-02-21

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
    parser.add_argument("tsv", help="a TSV including URIs")
    parser.add_argument("-d","--dry", help="doesn't update ArchivesSpace, used for testing", action="store_true")
    args = parser.parse_args()

    dry = False
    if args.dry:
        dry = True
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

    global config
    config = ConfigParser.ConfigParser()
    configFilePath = r'config.ini'
    config.read(configFilePath)

    id_field = 'id'
    classification_uri_field = 'classification_uri'
    
    # Initialize AS client
    aspace_client = ASClient(config.get('archivesspace','api-prefix'),
                             config.get('archivesspace','username'),
                             config.get('archivesspace','password'))
    repository = config.get('archivesspace','repository')

    with open(args.tsv, 'rU') as csvfile: #'rU' because Mac Excel exports are wierd
        reader = csv.DictReader(csvfile, delimiter='\t')
        for row in reader:

            # REPORT and SKIP if the do has no Archival Object URI
            if id_field and not row[id_field]:
                logging.warn('SKIPPING: no Resource ID (field: %s) for row: %s' % (id_field,json.dumps(row)))
                continue

            #  REPORT and SKIP if the do has no title
            if classification_uri_field and not row[classification_uri_field]:
                logging.warn('SKIPPING: no Classification URI for row: %s' % (json.dumps(row)))
                continue

            as_ao = aspace_client.api_call('/repositories/2/resources/%s' % row[id_field])

            # If the AS AO already has a DO with a matching URI, skip it.
            if as_ao['classifications']:
                continue
            
            as_classification = {'ref':row[classification_uri_field]}
            as_ao['classifications'].append(as_classification)
            if dry:
                logging.info('DRY: Would update AS Archival Resource %s with new classification %s' % (as_ao['uri'], as_classification))
            else:
                ao_update_response = aspace_client.api_call(as_ao['uri'],'POST', as_ao)
                if 'status' in ao_update_response:
                    logging.info('%s: AS Archival Resource %s with Classification %s' % (ao_update_response['status'],ao_update_response['id'],row[classification_uri_field]))
                else:
                    logging.info('Unable to update AS Archival Resource %s with Classification %s' % (as_ao['uri'],row[classification_uri_field]))
