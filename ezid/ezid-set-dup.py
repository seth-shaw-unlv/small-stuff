#!/usr/bin/python

import base64
import ConfigParser
import os, sys, logging, csv
import urllib, urllib2
import json

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

def query_ark(ark):
    request = urllib2.Request("%s/%s" % ('https://ezid.cdlib.org/id', ark))
    request.add_header("Content-Type", "text/plain; charset=UTF-8")

    try:
        logging.debug('Request URL: %s Data: %s'%(request.get_full_url(),request.get_data()))
        response = urllib2.urlopen(request)
        answer = response.read()
        return dict(s.split(': ',1) for s in answer.strip().split('\n'))

    except urllib2.HTTPError, e:
        logging.error("%d %s\n" % (e.code, e.msg))
        if e.fp != None:
          response = e.fp.read()
          if not response.endswith("\n"): response += "\n"
          logging.error("Can't mint ark. Response: %s", response)

if __name__ == '__main__':

    # Check arguments
    if len(sys.argv)<2:
        sys.exit("Please provide a file with a list of arks.")
    if os.path.isfile(sys.argv[1]) != True :
        sys.exit('"'+sys.argv[1] + '" is not a file. Please provide a file with the list of arks.')

    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

    global config
    config = ConfigParser.ConfigParser()
    configFilePath = r'config.ini'
    config.read(configFilePath)

    with open(sys.argv[1], 'rU') as f: #'rU' because Mac Excel exports are wierd
        for line in f:
            ark = line.strip()
            target = 'http://ezid.cdlib.org/id/' + ark
            dc = {
             'dc.title'    : 'DUPLICATE',
             'dc.date'     : '',
             'dc.creator'  : '',
             'dc.publisher': '',
             'dc.type'     : '',
             '_status'     : 'unavailable'
            }

            response = update_ark(ark,target,dc)
            print("\t".join((ark,response)))
            # print("\t".join((ark,target,json.dumps(dc))))
