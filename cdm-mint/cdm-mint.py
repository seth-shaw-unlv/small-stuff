#!/usr/bin/python

from suds.client import Client
import base64
import ConfigParser
import json
import logging
import argparse, sys
import urllib, urllib2

# Based on https://gist.github.com/saverkamp/9198310

# cdm-mint.py collection-alias
# Mints ARKS and updates CONTENTdm records with the Catcher protocol given a collection alias.
# CDM Catcher documentation at: http://contentdm.org/help6/addons/catcher.asp
# ***requires SUDS, a third-party SOAP python client: https://fedorahosted.org/suds/***

class Catcher(object):
    """A CONTENTdm Catcher session."""
    # Taken from saverkamp (https://gist.github.com/saverkamp/9197945)
    def __init__(self, url, user, password, license):
        self.transactions = []
        self.client = Client('https://worldcat.org/webservices/contentdm/catcher/6.0/CatcherService.wsdl')
        self.url = url
        self.user = user
        self.password = password
        self.license = license

    def checkLogin(self):
        transaction = self.client.service.getCONTENTdmCatalog(self.url,self.user,self.password,self.license)
        if '<title>401 Unauthorized</title>' in transaction:
            return False
        return True

    def processCONTENTdm(self, action, alias, metadata):
    # function to connect to CatcherServices and process metadata updates
        transaction = self.client.service.processCONTENTdm(action, self.url, self.user, self.password, self.license, alias, metadata)
        self.transactions.append(transaction)

    def edit(self, alias, recordid, field, value):
    #function to edit metadata--call packageMetadata and processCONTENTdm
        metadata = self.packageMetadata('edit', recordid, field, value)
        self.processCONTENTdm('edit', alias, metadata)

    def packageMetadata(self, action, recordid, field, value):
    #function to package metadata in metadata wrapper
        action = action
        if action == 'edit':
            metadata = self.client.factory.create('metadataWrapper')
            metadata.metadataList = self.client.factory.create('metadataWrapper.metadataList')
            metadata1 = self.client.factory.create('metadata')
            metadata1.field = 'dmrecord'
            metadata1.value = recordid
            metadata2 = self.client.factory.create('metadata')
            metadata2.field = field
            metadata2.value = value
            metadata.metadataList.metadata = [metadata1, metadata2]
        return metadata

class CDMQueryClient(object):
    """A CONTENTdm Query session."""
    def __init__(self, url):
        self.url = url + '/dmwebservices/index.php?q='

    # dmQuery/oclcsample/0/title!ark/pointer/5/0/1/0/0/1/json
    def query(self, alias, search='0', fields='0', sortby='0', maxrec=1024, start=1, suppress='1', docptr='0', suggest='0', facets='0', unpub='1', denormalize='1' ):
        """ Generator of search results. """
        alias = alias.lstrip('/')

        more = True
        while more == True:
            query= 'dmQuery/'+'/'.join((alias,search,fields,sortby,str(maxrec),str(start),suppress,docptr,suggest,facets,unpub,denormalize)) + '/json'
            logging.debug('Running %s' % (self.url + query))
            request = urllib2.Request(self.url + query)

            try:
                response = json.load(urllib2.urlopen(request))
            except urllib2.HTTPError as h:
                logging.error("Unable to process CONTENTdm wsAPI call (%s): %s - %s - %s" % (query, h.code, h.reason, h.read()))
                raise StopIteration
            except ValueError as v:
                logging.error("Invalid Response to CONTENTdm wsAPI call (%s): %s" % (query, v))
                raise StopIteration

            for record in response['records']:
                yield record

            # Paging
            if (maxrec+start) < response['pager']['total']:
                start += maxrec
            else:
                more = False


# who_what_when is a dict with the keys who, what, and when. All other keys are ignored.
def mint_ark(target, dublin_core={}):
    request = urllib2.Request("%s/%s" % (config.get('ezid','minter-url'),
                              config.get('ezid','ark-shoulder')))
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
            logging.info('Minted ARK for %s : %s' % (target,ark))
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
    parser.add_argument("alias", help="a CONTENTdm collection alias", nargs='+')
    parser.add_argument("-q","--query", help='a CONTENTdm dmQuery "searchstrings" to narrow items for minting. E. g., "origin^Donn%%20Arden%%20Papers^exact".')
    parser.add_argument("-k","--ark-field", help='the CONTENTdm field to use for the object ARKs (overrides config.ini)')
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

    query = '0'
    if args.query:
        query = args.query

    dc_profile = ['title','creator','contributor','publisher','date','extent','format','type','relation']

    #Setup the Catcher Service
    catcher = Catcher(config.get('cdm','catcher-url'),
                      config.get('cdm','username'),
                      config.get('cdm','password'),
                      config.get('cdm','license')
                     )

    # Check login
    if not catcher.checkLogin():
        sys.exit("Could not connect to the catcher service.\nPease check your connection settings (catcher-url, username, password, and license).")

    # Which field holds the ARK?
    ark_field = config.get('cdm','ark-field')
    if args.ark_field:
        ark_field = args.ark_field

    # Gather all the items in a CONTENTdm collection
    dmQuery = CDMQueryClient(config.get('cdm','wsAPI-url'))

    for alias in args.alias:

        alias = alias.lstrip('/') # The preceding / on an alias is annoying to work with. Chop it off if present.

        for result in dmQuery.query(alias,query,'!'.join(dc_profile)+'!'+ark_field):
            # Next if it has an ARK
            if ark_field in result and 'ark:' in result[ark_field]:
                logging.info('Resource %s in %s already has an ARK (%s); skipping...' % (result['pointer'],result['collection'],result[ark_field]))
                continue

            # remove the blank DC fields
            dc_values = dict()
            for field in dc_profile:
                # NOTE: the EZID service requires a 'dc.' prefix whereas CDM doesn't use one.
                if field in result and len(result[field]) > 0 : dc_values['dc.'+field] = result[field]

            # Construct the target url
            resource_url = config.get('cdm','public-url') % (result['collection'].lstrip('/'),result['pointer'])
            logging.debug('%s : %s' % (resource_url, json.dumps(dc_values)))

            # Mint the ARK
            if args.dry:
                logging.info('TESTING, would mint an ark for %s' % (resource_url))
            else:
                new_ark = mint_ark(resource_url,dc_values)
                # Update the resource's ARK using Catcher
                catcher.edit(result['collection'], str(result['pointer']), ark_field, config.get('ezid','ark-resolver')+new_ark)

    logging.info('CDM Catcher Transactions: '+json.dumps(catcher.transactions))
