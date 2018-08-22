#!/usr/bin/python

import base64
import os, sys, logging, csv
import urllib, urllib2

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
        writer = csv.DictWriter(sys.stdout, fieldnames=['success','_target','_status','dc.type','dc.title','dc.date','dc.relation'], extrasaction='ignore')
        writer.writeheader()
        for row in reader:
            # Strip http://n2t.net/ from the beginning (if it is there)
            ark = row['_id'].lstrip('htps:/n2t.e') 
            metadata = query_ark(ark)
            writer.writerow(metadata)
