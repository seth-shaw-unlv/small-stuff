#!/usr/bin/python

import json
import urllib, urllib2
import base64
import os, sys, ConfigParser, logging, csv
import datetime

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

    # Once we find the uri for a collection we need to hold on to it so we can
    # pull it up directly instead of using the outdated search
    MSS_index = {}

    #We will need today later
    today = datetime.datetime.now().isoformat('T')


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

    # EACH spreadsheet row

    if len(sys.argv)<2:
        sys.exit("Please provide locations spreadsheet.")
    if os.path.isfile(sys.argv[1]) != True :
        sys.exit('"'+sys.argv[1] + '" is not a file. Please provide the locations spreadsheet.')

    with open(sys.argv[1], 'rU') as csvfile: #'rU' because Mac Excel exports are wierd

        reader = csv.DictReader(csvfile, dialect=csv.excel_tab)
        for row in reader:
            # Find the collection by MS
            if not 'Location' in row.keys():
                print "Location for this row not found"
            elif not 'Collection number' in row.keys():
                print '%s has no collection number associated with it' % row['Location']
            elif row['Collection number'] == '':
                print '%s appears empty' % (row['Location'])
            elif not row['Collection number'].startswith('MS'):
                print '%s has something other than an MS: %s' % (row['Location'], row['Collection number'])
            else:
                # So good so far, we have all the pieces from the CSV we need.
                resource = {}
                if row['Collection number'] in MSS_index.keys(): #We've done this collection before.
                    logging.debug("Found %s before, asking for it again in case of update" % (row['Collection number']))
                    results_obj = archivesspace_api_call(MSS_index[row['Collection number']])
                    resource = {'obj':results_obj, 'identifier':row['Collection number'], 'id':results_obj['uri']}
                else:
                    logging.debug("Looking up %s for the first time" % row['Collection number'])
                    results_obj = archivesspace_api_call("/repositories/%s/search" % config.get('archivesspace', 'repository'),data={'q':'identifier:'+row['Collection number'],'page':'1','page_size':'1'})

                    if not 'results' in results_obj.keys() or not results_obj['results'] or results_obj['results'][0]['identifier'] != row['Collection number']:
                        print '%s has %s but couldn\'t find it in AS:\t%s' % (row['Location'], row['Collection number'], parse_containers(row['Container']))
                        continue
                    else:
                        resource = {'obj':json.loads(results_obj['results'][0]['json']),'identifier':results_obj['results'][0]['identifier'],'id':results_obj['results'][0]['id']}
                        MSS_index[row['Collection number']] = resource['id']

                # CAN'T remove lock_version, AS will throw a 409 - Conflict error demanding you provide one. It looks like the indexer isn't keeping up.
                # print "%s lock version %s, attempting to remove it...." %(resource['identifier'], resource['obj']['lock_version'])
                # resource['obj'].pop('lock_version', None)
                # print(json.dumps(resource, indent=4))
                print "%s has %s (%s):\t%s" % (row['Location'], resource['identifier'], resource['id'], parse_containers(row['Container']))
                # Find Location URI in hash
                location_code = format('%s %s') % (row['Room'].strip(),row['Location'].strip())
                if location_code in locations.keys():
                    # print 'Found location %s: %s' % (locations[location_code], location_code)

                    # Create a top-level container

                    # Possible container types: box, carton, case, folder, frame, object, reel
                    container_type = 'box' # We may make this more dynamic now, but assume boxes for now.

                    instances = [] # All the containers we will add to the collection located here

                    for container_number in parse_containers(row['Container']):
                        container_number = str(container_number) #sometimes we get integers, but we want strings to use string functions
                        if container_number.isdigit():
                            # Check if they exist
                            existing = False #assume missing unless proven otherwise
                            for instance in resource['obj']['instances']:
                                if instance['container']['indicator_1'] == container_number:
                                    existing = True
                                    break #no need to keep checking
                            #IF missing
                            if not existing:
                                top_container = {'jsonmodel_type':'top_container',
                                                 'container_locations':
                                                    [
                                                        {
                                                            'jsonmodel_type':'container_location',
                                                            'ref':locations[location_code],
                                                            'status':'current',
                                                            'start_date':today
                                                        }
                                                     ],
                                                 'indicator':container_number,
                                                 'type':container_type
                                                }
                                # POST Top container
                                response_obj = archivesspace_api_call('/repositories/%s/top_containers' % (config.get('archivesspace', 'repository')),'POST', json.dumps(top_container))
                                # if not 'status' in response_obj.keys or not response_obj['status'] == 'Created':
                                #     print "Could not create top container for %s: %s" % (resource['identifier'],json.dumps(top_container))
                                #     break
                                logging.debug('Response to creating a top container %s: %s' % (json.dumps(top_container), json.dumps(response_obj)))
                                # print json.dumps(top_container)
                                tc_uri = response_obj['uri'] #place-holder until the POST goes live
                                # Create Instance
                                instances.append({ "instance_type": "text",
                                             "jsonmodel_type": "instance",
                                             "is_representative": False,
                                             "sub_container": {
                                                "jsonmodel_type": "sub_container",
                                                "top_container": { "ref": tc_uri }
                                              },
                                              "container": {
                                                "type_1": container_type,
                                                "indicator_1": container_number,
                                                "container_locations": [
                                                  {
                                                    "jsonmodel_type": "container_location",
                                                    "status": "current",
                                                    "start_date": today.partition('T')[0],
                                                    "ref": locations[location_code]
                                                  }
                                                ]
                                              }
                                            })
                            else:
                                print "%s already has %s in %s" % (resource['identifier'], container_number, location_code)
                        else:
                            print ("%s has a non-standard container (%s) in location %s" % (resource['identifier'], container_number, location_code))
                        # print "Instances for "+ resource['identifier'] +" ("+ resource['id']+"): "+json.dumps(instances)

                    #POST resource IF instances isn't empty
                    if instances:
                        resource['obj']['instances'].extend(instances)
                        # print "Instances for "+ resource['identifier'] +" ("+ resource['id']+"): "+json.dumps(resource['obj']['instances'])
                        response_obj = archivesspace_api_call(resource['id'],'POST', json.dumps(resource['obj']))
                        logging.debug('Response to updating %s: %s' % (resource['identifier'], json.dumps(response_obj)))

                else:
                    print 'Couldn\'t find %s' % location_code
