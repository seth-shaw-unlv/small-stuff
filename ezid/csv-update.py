#!/usr/bin/python

from suds.client import Client
import base64
import ConfigParser
import csv, codecs, cStringIO, sys
import io
import json
import logging
import argparse
import urllib, urllib2
import re
import requests

# Unicode support
# https://gist.github.com/eightysteele/1174811/0cce72809ff71bed6212599c677925b338f94878
class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

class UnicodeDictReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)
        self.header = self.reader.next()

    def next(self):
        row = self.reader.next()
        vals = [unicode(s, "utf-8") for s in row]
        return dict((self.header[x], vals[x]) for x in range(len(self.header)))

    def __iter__(self):
        return self
    
class UnicodeDictWriter:
    def __init__(self, f, fieldnames, restval="", extrasaction="raise",
                 dialect="excel", encoding="utf-8", *args, **kwds):
        self.fieldnames = fieldnames    # list of keys for the dict
        self.restval = restval          # for writing short dicts
        if extrasaction.lower() not in ("raise", "ignore"):
            raise ValueError("extrasaction (%s) must be 'raise' or 'ignore'"
                             % extrasaction)
        self.extrasaction = extrasaction
        self.writer = csv.writer(f, dialect, *args, **kwds)
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writeheader(self):
        header = dict(zip(self.fieldnames, self.fieldnames))
        self.writerow(header)

    def _dict_to_list(self, rowdict):
        if self.extrasaction == "raise":
            wrong_fields = rowdict.keys() - self.fieldnames
            if wrong_fields:
                raise ValueError("dict contains fields not in fieldnames: "
                                 + ", ".join([repr(x) for x in wrong_fields]))
        return list(rowdict.get(key, self.restval) for key in self.fieldnames)

    def writerow(self, rowdict):
        rowlist = self._dict_to_list(rowdict)
        return self.writer.writerow([self.encoder.encode(x) for x in rowlist])

    def writerows(self, rowdicts):
        return self.writer.writerows(map(self._dict_to_list, rowdicts))

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

# escape special characters for anvl metadata (from the EZID API doc)
def escape (s):
    return re.sub("[%:\r\n]", lambda c: "%%%02X" % ord(c.group(0)), s)

# who_what_when is a dict with the keys who, what, and when. All other keys are ignored.
def update_ark(ark, fields={}):
    url = (u"%s/%s" % (config.get('ezid','update-url'),ark))
    #Authentication
    encoded_auth = base64.encodestring('%s:%s' % (config.get('ezid','username'),
                                                  config.get('ezid','password')
                                                  )).replace('\n', '')    
    headers = {
        u'Content-Type': u'text/plain; charset=UTF-8',
        u'Authorization': u"Basic %s" % encoded_auth
    }
    #Add profile
    data = u"_profile: dc\n"
    for descriptive_item_term, descriptive_item_value in fields.iteritems():
        data += u'%s: %s\n' % (escape(descriptive_item_term), escape(descriptive_item_value))
        
    try:
        r = requests.post(url, headers=headers, data=data.encode('utf-8'))
        logging.debug(u'Request URL: %s Data: %s'%(r.url,data))
        answer = r.text
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
    url = (u"%s/%s" % (config.get('ezid','update-url'),ark))
    #Authentication
    encoded_auth = base64.encodestring('%s:%s' % (config.get('ezid','username'),
                                                  config.get('ezid','password')
                                                  )).replace('\n', '')    
    headers = {
        u'Content-Type': u'text/plain; charset=UTF-8',
        u'Authorization': u"Basic %s" % encoded_auth
    }
    #Add profile
    data = u"_profile: dc\n"
    for descriptive_item_term, descriptive_item_value in fields.iteritems():
        data += u'%s: %s\n' % (escape(descriptive_item_term), escape(descriptive_item_value))
        
    try:
        r = requests.post(url, headers=headers, data=data.encode('utf-8'))
        logging.debug(u'Request URL: %s Data: %s'%(r.url,data))
        answer = r.text
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
        'dc.contributor','dc.description','dc.publisher','dc.rights',
        'dc.isPartOf','_status','_target'
        ]

    current_as_rid = None
    current_cid = None
    reader = UnicodeDictReader(open(args.csv, 'r'), delimiter='\t')
    writer = UnicodeDictWriter(sys.stdout, fieldnames=['_id','_target','_status','dc.identifier','dc.type','dc.title','dc.date','dc.isPartOf','dc.creator','dc.contributor'], delimiter='\t', extrasaction='ignore')
    writer.writeheader()
    for row in reader:
        # only pass supported values
        dc_values = dict()
        for field in supported_fields:
            if field in row and row[field]:
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
