#!/usr/bin/python

import json
import urllib, urllib2
import base64
import os, sys, ConfigParser, logging, csv

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


def parse_containers(to_parse):
    containers = []

    #Clean-up input
    to_parse = to_parse.partition(' of ')[0] #trim box count if provided
    to_parse = to_parse.lower()
    to_parse = to_parse.replace('boxes','') #Clean up and remove default "Boxes"
    to_parse = to_parse.replace('box','') #Clean up and remove default "Boxes"
    to_parse = to_parse.strip() #Clean up and remove default "Boxes"

    for group in to_parse.split(','):
        if '-' in group:
            (start, part, end) = group.partition('-')
            if start.strip().isdigit() and end.strip().isdigit():
                containers.extend(range(int(start),int(end)+1))
            else:
                containers.append(group.strip())
        elif 'to' in group:
            (start, part, end) = group.partition('to')
            if start.strip().isdigit() and end.strip().isdigit():
                containers.extend(range(int(start),int(end)+1))
            else:
                containers.append(group.strip())
        elif ' and ' in group:
            containers.extend(group.split(' and '))
        else:
            containers.append(group.strip())

    return containers


if __name__ == '__main__':

    # logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
    #                     filename='location-migration.log',level=logging.DEBUG)
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

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
        # print("Page %s of %s" % (next_page, last_page))
        # print(json.dumps(location_obj))
        if location_obj['last_page'] != last_page:
            # print('Updating last page from %s to %s' % (last_page, location_obj['last_page']))
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

    if len(sys.argv)<2:
        sys.exit("Please provide locations spreadsheet.")
    if os.path.isfile(sys.argv[1]) != True :
        sys.exit('"'+sys.argv[1] + '" is not a file. Please provide the locations spreadsheet.')

    with open(sys.argv[1], 'rU') as csvfile:

        reader = csv.DictReader(csvfile, dialect=csv.excel_tab)
        for row in reader:
            # print 'Room: %s\tArea: %s\tColl id: %s\tColl title: %s\tContainer: %s' % (row['Room'],row['Location'],row['Collection number'],row['Collection Title'],row['Container']) #Room	Location	Collection number	Collection Title	Container	Original Collection Title
            # Find the collection by MS

            # SET ASIDE WHILE WORKING ON OTHER CODE
            # if not 'Location' in row.keys():
            #     print "Location for this row not found"
            # elif not 'Collection number' in row.keys():
            #     print '%s has no collection number associated with it' % row['Location']
            # elif row['Collection number'] == '':
            #     print '%s appears empty' % (row['Location'])
            # elif not row['Collection number'].startswith('MS'):
            #     print '%s has something other than an MS: %s' % (row['Location'], row['Collection number'])
            # else:
            #     results_obj = archivesspace_api_call("/repositories/%s/search" % config.get('archivesspace', 'repository'),data={'q':row['Collection number'],'page':'1','page_size':'1'})
            #     if not 'results' in results_obj.keys() or not results_obj['results'] or results_obj['results'][0]['identifier'] != row['Collection number']:
            #         print '%s has %s but couldn\'t find it in AS:\t%s' % (row['Location'], row['Collection number'], parse_containers(row['Container']))
            #     else:
            #         print "%s has %s (%s):\t%s" % (row['Location'], results_obj['results'][0]['identifier'], results_obj['results'][0]['id'], parse_containers(row['Container']))

            # Find Location URI in hash
            location_code = format('%s %s') % (row['Room'].strip(),row['Location'].strip())
            if location_code in locations.keys():
                print 'Found location %s: %s' % (locations[location_code], location_code)
            else:
                print 'Couldn\'t find %s' % location_code
            # Create a top-level container
            # Create Instance
