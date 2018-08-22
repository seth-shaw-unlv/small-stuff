#!/usr/bin/python

import base64
import os, sys, logging, csv
import urllib, urllib2

def update_ark(ark, target):
    request = urllib2.Request("%s/%s" % ('https://ezid.cdlib.org/id', ark))
    request.add_header("Content-Type", "text/plain; charset=UTF-8")

    #Authentication
    encoded_auth = base64.encodestring('%s:%s' % ('REMOVED USERNAME','REMOVED PASSWORD')).replace('\n', '')
    request.add_header("Authorization","Basic %s" % encoded_auth)

    #Add target URL
    data = "_target: %s" % (target)

    request.add_data(data.encode("UTF-8"))

    try:
        logging.debug('Request URL: %s Data: %s'%(request.get_full_url(),request.get_data()))
        response = urllib2.urlopen(request)
        answer = response.read()
        if answer.startswith('success'):
            return answer
        else:
            logging.error("Can't mint ark: %s", answer)
            return ''
    except urllib2.HTTPError, e:
        logging.error("%d %s\n" % (e.code, e.msg))
        if e.fp != None:
          response = e.fp.read()
          if not response.endswith("\n"): response += "\n"
          logging.error("Can't mint ark. Response: %s", response)

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
        sys.exit("Please provide CSV with arks in an '_id' field.")
    if os.path.isfile(sys.argv[1]) != True :
        sys.exit('"'+sys.argv[1] + '" is not a file. Please provide the CSV of arks.')

    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

    with open(sys.argv[1], 'rU') as csvfile: #'rU' because Mac Excel exports are wierd

        reader = csv.DictReader(csvfile)
        for row in reader:
            target = query_ark(row['_id'])['_target']
            if not 'https://' in target: continue
            new_target = target.replace('https://','http://')
            response = update_ark(row['_id'],new_target)
            print("\t".join((row['_id'],target,new_target,response)))
