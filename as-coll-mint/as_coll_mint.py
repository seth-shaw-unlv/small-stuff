#!/usr/bin/python

import base64
import ConfigParser
import csv
import json
import logging
import os
import sys
import urllib, urllib2

# as_coll_mint.py takes a spreadsheet of resources (must include id,
# identifier; optionally include ead_location), mints an ARK, updates the
# resources' ead_location, and exports a PDF.
#
# @author Seth Shaw
# @date 2017-08-02
#
# Before running the configuration file must be complete.
# Copy config.ini.example to config.ini and update the necessary values.
#
# Note that this script assumes all resources are from the same repository.
# The repository id is set in the config.ini file.

SESSION = ''

def mint_ark(identifier):
    request = urllib2.Request("%s/%s" % (config.get('ezid','minter-url'),
                              config.get('ezid','ark-shoulder')))
    request.add_header("Content-Type", "text/plain; charset=UTF-8")

    #Authentication
    encoded_auth = base64.encodestring('%s:%s' % (config.get('ezid','username'),
                                                  config.get('ezid','password')
                                                  )).replace('\n', '')
    request.add_header("Authorization","Basic %s" % encoded_auth)

    #Add target URL
    target = "%s/%s.pdf" % (config.get('archivesspace','pdf-url-prefix'),
                            identifier )
    data = ("_target: %s" % (target))
    request.add_data(data.encode("UTF-8"))

    try:
        response = urllib2.urlopen(request)
        answer = response.read()
        if answer.startswith('success'):
            code,ark = answer.split(": ")
            logging.info('Minted ARK for %s: %s => %s' % (identifier,
                                                          ark, target))
            return ark
        else:
            logging.error("Can't mint ark: %s", answer)
            return ''
    except urllib2.HTTPError, e:
        logging.error("%d %s\n" % (e.code, e.msg))
        if e.fp != None:
          response = e.fp.read()
          if not response.endswith("\n"): response += "\n"
          logging.error("Can't mint ark. Response: %s", response)

def update_ead_location(id, location):
    #pull JSON object for resource
    resource = archivesspace_api_call(
            '/repositories/%s/resources/%s' % (config.get('archivesspace',
                                                          'repository'),id))

    #update ead_location field if it doesn't already match
    if (('ead_location' not in resource.keys())
    or (location != resource['ead_location'])):
        resource['ead_location'] = location #update the existing object
        archivesspace_api_call('/repositories/%s/resources/%s' % (
                    config.get('archivesspace', 'repository'),id),
                'POST', json.dumps(resource))

def export_fa_pdf(id, identifier):

    if not os.path.isdir(config.get('pdf','export-location')):
         #prep the path for exporting files
        os.makedirs(os.path.normpath(config.get('pdf','export-location')))

    with open(os.path.normpath('%s/%s.pdf' % (config.get('pdf','export-location'), identifier )), "wb") as local_file:
        local_file.write(archivesspace_api_call("/repositories/%s/resource_descriptions/%s.pdf" % (config.get('archivesspace', 'repository'), id ), as_obj = False).read())

def archivesspace_api_call(path, method = 'GET', data = {}, as_obj = True):

    #empty SESSION, we should log in, but not if we are trying to login now.
    if not SESSION and not path.endswith('login'):
        archivesspace_login()
    path = config.get('archivesspace','api-prefix') + path

    # urllib2 will force a call to POST if the data element is provided.
    # So, a query string must be appended to path if you want a GET
    if method == 'GET':
        if data:
            request = urllib2.Request(path + '?' + urllib.urlencode(data))
        else:
            request = urllib2.Request(path)
    elif method == 'POST':
        request = urllib2.Request(path, data)
    else:
        logging.error("Unknown or unused HTTP method: %s" % method)
        return

    if SESSION:
        request.add_header("X-ArchivesSpace-Session",SESSION)

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

def archivesspace_login():
    global SESSION
    path = '/users/%s/login' % config.get('archivesspace','username')
    obj = archivesspace_api_call(path,
                                'POST',
                                urllib.urlencode(
                                    {'password':config.get('archivesspace',
                                        'password') }))
    SESSION = obj["session"]

if __name__ == '__main__':

    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                        filename='as-coll-mint.log',level=logging.INFO)

    global config
    config = ConfigParser.ConfigParser()
    configFilePath = r'config.ini'
    config.read(configFilePath)

    if len(sys.argv)<2:
        sys.exit("Please provide a TSV with id and identifer columns.")
    if os.path.isfile(sys.argv[1]) != True :
        sys.exit('"'+sys.argv[1] + '" is not a file. Please provide a TSV with id and identifer columns.')

    with open(sys.argv[1]) as csvfile:

        reader = csv.DictReader(csvfile, delimiter='\t')
        for row in reader:
            print(row['id'], row['identifier'])

            # Clean collection identifiers if necessary
            if '[' in row['identifier']: #identifier list straight from DB, let's clean it up
                identifier = ''
                #join chokes on unused identifier fields (null values), loop instead
                for f in json.loads(row['identifier']):
                    # concatenate but don't include null fields
                    identifier += ( f + '-' ) if f else ''

                #pull off the extraneous hyphens and return
                row['identifier'] = identifier.rstrip('-')
                logging.info('Cleaned identifier for %s: %s' % (row['id'], row['identifier']))

            # MINT the ark
            if 'ark:' in row['ead_location']:
                ark = row['ead_location']
                logging.info('Existing ARK for %s: %s' % (row['identifier'],ark))
            else:
                ark = '%s/%s' % (config.get('ezid','ark-resolver'),mint_ark(row['identifier']))

            # UPDATE ArchivesSpace EAD Location
            update_ead_location(row['id'],ark)

            # EXPORT PDF
            export_fa_pdf(row['id'],row['identifier'])

    ## Testing API Calls so we don't have to rely on a spreadsheet export...
    ## Could use /repositories/:id/resources but I would rather not retrieve every resource just to find the ones I want...
    ## Search narrows down the results to published (or not) resources, but doesn't like searching ead_location...
    ## Bah, long live SQL queries to TSV.

    # print(json.dumps(archivesspace_api_call("/repositories/%s/resources" % config.get('archivesspace', 'repository'), 'GET', {"page": '1', 'page_size':'2'}), indent = 2))
    # print(json.dumps(archivesspace_api_call("/search", data = {'page':'1','type[]':'resource','aq':json.dumps({'query':{'field':'title','value':'Test','jsonmodel_type':'field_query'}})}), indent = 2))
    # print(json.dumps(archivesspace_api_call("/search",
    #     data = {'page':'1', 'page_size':'1',
    #             'type[]':'resource',
    #             'aq':json.dumps({'query':
    #                                 {'op':'AND',
    #                                 'subqueries':[
    #                                     {'field':'title','value':'Test','jsonmodel_type':'field_query'},
    #                                     {'field':'published','value':'true','jsonmodel_type':'boolean_field_query'}],
    #                                     ],
    #                                 'jsonmodel_type':'boolean_query'
    #                                 },
    #                               'jsonmodel_type':'advanced_query'
    #                             })
    #             }), indent = 2))
    # print(json.dumps(archivesspace_api_call("/search",
    #             data = {'page':'1','page_size':'1',
    #                     'type[]':'resource',
    #                     'aq':json.dumps(
    #                             {'query':
    #                                 {'field':'published',
    #                                 'value':'true',
    #                                 'jsonmodel_type':'boolean_field_query'
    #                                 }
    #                             }
    #                     )
    #             }
    #         ),indent = 2)
    # )
