#!/usr/bin/python

import json
import logging
import urllib, urllib2
import base64
import ConfigParser

TEST = True
SESSION = ''

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
                        filename='location-migration.log',level=logging.INFO)

    global config
    config = ConfigParser.ConfigParser()
    configFilePath = r'config.ini'
    config.read(configFilePath)

    # LOAD Location URIs into a hash table
    # locations are paginated, iterate through them
    locations = {}

    next_page = 1
    last_page = 1 #assume one page until told otherwise
    page_size = 200
    while next_page <= last_page:
        location_obj = archivesspace_api_call('/locations', data={'page':next_page, 'page_size':page_size})
        print("Page %s of %s" % (next_page, last_page))
        # print(json.dumps(location_obj))
        if location_obj['last_page'] != last_page:
            print('Updating last page from %s to %s' % (last_page, location_obj['last_page']))
            last_page = location_obj['last_page']
        for location in location_obj['results']:
            coords = ''
            for c in ['coordinate_1_indicator','coordinate_2_indicator','coordinate_3_indicator']:
                if c in location.keys():
                    if location[c].isdigit() and c != 'coordinate_3_indicator': #final coordinate is never buffed.
                        coords += format(int(location[c]),'02d')
                    else: #A-Z coordinates
                        coords += location[c]
                coords += '.'
            coords = coords.rstrip('.')
            # print('Room: %s Coordinates: %s URI: %s' % (location['room'],coords, location['uri']))
            locations[format('%s %s') % (location['room'],coords)] = location['uri']
        next_page += 1

    # print json.dumps(locations, sort_keys=True, indent=4)
    # EACH spreadsheet row

    # Find the collection by MS

    # Create a top-level container
