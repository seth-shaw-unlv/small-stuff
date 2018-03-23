"CONTENTdm (CDM) Module"

from suds.client import Client
import json
import logging
import urllib, urllib2

class CatcherSession(object):
    """A CONTENTdm Catcher session."""
    # Taken from saverkamp (https://gist.github.com/saverkamp/9197945)
    # CDM Catcher documentation at: http://contentdm.org/help6/addons/catcher.asp
    # ***requires SUDS, a third-party SOAP python client: https://fedorahosted.org/suds/***
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

class QueryClient(object):
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
