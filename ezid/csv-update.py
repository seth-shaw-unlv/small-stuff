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
def update_ark(ark, fields={}):
    request = urllib2.Request("%s/%s" % (config.get('ezid','update-url'),ark))
    request.add_header("Content-Type", "text/plain; charset=UTF-8")

    #Authentication
    encoded_auth = base64.encodestring('%s:%s' % (config.get('ezid','username'),
                                                  config.get('ezid','password')
                                                  )).replace('\n', '')
    request.add_header("Authorization","Basic %s" % encoded_auth)

    #Add profile
    data = "_profile: %s\n" % ('dc')
    for descriptive_item_term, descriptive_item_value in fields.iteritems():
        data += '%s: %s\n' % (descriptive_item_term, descriptive_item_value)

    request.add_data(data.encode("UTF-8"))

    try:
        logging.debug('Request URL: %s Data: %s'%(request.get_full_url(),request.get_data()))
        response = urllib2.urlopen(request)
        answer = response.read()
        if answer.startswith('success'):
            code,ark = answer.split(": ")
            logging.debug('Updated ARK: %s' % (ark))
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

def mint_ark(fields={}):
    request = urllib2.Request("%s/%s" % (config.get('ezid','minter-url'),
                              config.get('ezid','ark-shoulder')))
    request.add_header("Content-Type", "text/plain; charset=UTF-8")

    #Authentication
    encoded_auth = base64.encodestring('%s:%s' % (config.get('ezid','username'),
                                                  config.get('ezid','password')
                                                  )).replace('\n', '')
    request.add_header("Authorization","Basic %s" % encoded_auth)

    #Add profile
    data = "_profile: %s\n" % ('dc')
    for descriptive_item_term, descriptive_item_value in fields.iteritems():
        data += '%s: %s\n' % (descriptive_item_term, descriptive_item_value)

    request.add_data(data.encode("UTF-8"))

    try:
        logging.debug('Request URL: %s Data: %s'%(request.get_full_url(),request.get_data()))
        response = urllib2.urlopen(request)
        answer = response.read()
        if answer.startswith('success'):
            code,ark = answer.split(": ")
            logging.debug('Minted ARK: %s' % (ark))
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


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("csv", help="a CSV records w/ ARKs")
    parser.add_argument("-v","--verbosity", help="change output verbosity: DEBUG, INFO (default), ERROR")
    parser.add_argument("-d","--dry", help="doesn't mint or update, used to test searchstrings", action="store_true")
    args = parser.parse_args()

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

    supported_fields = [
        'dc.title','dc.type','dc.identifier','dc.date','dc.creator',
        'dc.contributor','dc.isPartOf','_status','_target'
        ]

    with open(args.csv, 'rU') as csvfile: #'rU' because Mac Excel exports are wierd
        current_as_rid = None
        current_cid = None
        reader = csv.DictReader(csvfile, delimiter='\t')
        writer = csv.DictWriter(sys.stdout, fieldnames=['_id','_target','_status','dc.identifier','dc.type','dc.title','dc.date','dc.isPartOf','dc.creator','dc.contributor'], extrasaction='ignore')
        writer.writeheader()
        for row in reader:
            # only pass supported values
            dc_values = dict()
            for field in supported_fields:
                if field in row:
                    dc_values[field] = row[field].strip()

            if '_id' in row and row['_id']: # Update an ARK
                # Update the ARK
                if not args.dry:
                    update_ark(row['_id'],dc_values)

                dc_values['_id'] = row['_id']

            else: # Mint an ARK
                if args.dry:
                    dc_values['_id'] = 'ark:/FAKE_ARK'
                else:
                    new_ark = mint_ark(dc_values)
                    dc_values['_id'] = new_ark
            writer.writerow(dc_values)
