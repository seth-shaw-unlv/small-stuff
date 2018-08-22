#!/usr/bin/python

from suds.client import Client
import base64
import ConfigParser
import csv
import json
import logging
import argparse, sys
import urllib, urllib2

# who_what_when is a dict with the keys who, what, and when. All other keys are ignored.
def update_ark(ark, target, dublin_core={}):
    request = urllib2.Request("%s/%s" % (config.get('ezid','update-url'),ark))
    request.add_header("Content-Type", "text/plain; charset=UTF-8")

    #Authentication
    encoded_auth = base64.encodestring('%s:%s' % (config.get('ezid','username'),
                                                  config.get('ezid','password')
                                                  )).replace('\n', '')
    request.add_header("Authorization","Basic %s" % encoded_auth)

    #Add target URL
    data = "_target: %s\n_profile: %s\n" % (target,'dc')
    for descriptive_item_term, descriptive_item_value in dublin_core.iteritems():
        data += '%s: %s\n' % (descriptive_item_term, descriptive_item_value)

    request.add_data(data.encode("UTF-8"))

    try:
        logging.debug('Request URL: %s Data: %s'%(request.get_full_url(),request.get_data()))
        response = urllib2.urlopen(request)
        answer = response.read()
        if answer.startswith('success'):
            code,ark = answer.split(": ")
            logging.info('Updated ARK for %s : %s' % (target,ark))
            return ark
        else:
            logging.error("Can't update ark: %s", answer)
            return ''
    except urllib2.HTTPError, e:
        logging.error("%d %s\n" % (e.code, e.msg))
        if e.fp != None:
          response = e.fp.read()
          if not response.endswith("\n"): response += "\n"
          logging.error("Can't update ark. Response: %s", response)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("csv", help="a CSV records w/ ARKs")
    parser.add_argument("-v","--verbosity", help="change output verbosity: DEBUG, INFO (default), ERROR")
    parser.add_argument("-d","--dry", help="doesn't mint or update, used to test searchstrings", action="store_true")
    args = parser.parse_args()

    # if len(sys.argv) < 2 : sys.exit('Please provide a collection alias')

    # alias = sys.argv[1].lstrip('/') # The preceding / on an alias is annoying to work with. Chop it off if present.

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

    with open(args.csv, 'rU') as csvfile: #'rU' because Mac Excel exports are wierd
        current_as_rid = None
        current_cid = None
        reader = csv.DictReader(csvfile, delimiter='\t')
        for row in reader:

            # remove the blank DC fields
            dc_values = dict()
            # dc_values['dc.type'] = row['dc_type']
            dc_values['dc.title'] = row['title']
            # dc_values['dc.date'] = row['date']
            dc_values['dc.identifier'] = row['did']
            dc_values['_status'] = 'public'

            # Mint the ARK
            if args.dry:
                # logging.info('TESTING, would update an ark (%s) for %s' % (row['ark'],row['ref_url']))
                # print json.dumps(row)
                print("\t".join((row['ark'],row['ref_url'],json.dumps(dc_values))))
            else:
                new_ark = update_ark(row['ark'],row['ref_url'],dc_values)
