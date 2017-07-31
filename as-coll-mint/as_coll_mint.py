#!/usr/bin/python

import base64
import ConfigParser
import csv
import logging
import os
import sys
import urllib2

def mint_ark(config, identifier):
    request = urllib2.Request("%s/%s" % (config.get('ezid','minter-url'),config.get('ezid','ark-shoulder')))
    request.add_header("Content-Type", "text/plain; charset=UTF-8")

    #Authentication
    encoded_auth = base64.encodestring('%s:%s' % (config.get('ezid','username'),config.get('ezid','password'))).replace('\n', '')
    request.add_header("Authorization","Basic %s" % encoded_auth)

    #Add target URL
    data = ("_target: %s/%s.pdf" % (config.get('archivesspace','pdf-url-prefix'), identifier ))
    request.add_data(data.encode("UTF-8"))

    try:
        response = urllib2.urlopen(request)
        answer = response.read()
        if answer.startswith('success'):
            code,ark = answer.split(": ")
        return ark
    except urllib2.HTTPError, e:
        logging.error("%d %s\n" % (e.code, e.msg))
        if e.fp != None:
          response = e.fp.read()
          if not response.endswith("\n"): response += "\n"
          logging.error("Can't mint ark. Response: %s", response)


if __name__ == '__main__':

    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                        filename='as-coll-mint.log',level=logging.DEBUG)

    config = ConfigParser.ConfigParser()
    configFilePath = r'config.ini'
    config.read(configFilePath)

    if len(sys.argv)<2:
        sys.exit("Please provide a TSV with id and identifer columns.")
    if os.path.isfile(sys.argv[1]) != True :
        sys.exit('"'+sys.argv[1] + '" is not a file. Please provide a TSV with id and identifer columns.')

    # When we are ready to do each one.... testing for now.
    # with open(sys.argv[1]) as csvfile:
    #
    #     # The csv file I have has multiple columns and DictReader allows us to get just the ones we need by name
    #     reader = csv.DictReader(csvfile, delimiter='\t')
    #     for row in reader:
    #         print(row['id'], row['identifier'])
    #
    #     # MINT the ark - DONE
    #     # UPDATE ArchivesSpace EAD Location
    #     # Export PDF

    # test minting an ark: print(mint_ark(config, 'MS-TEST'))
