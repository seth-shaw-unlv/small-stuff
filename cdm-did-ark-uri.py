#! /usr/bin/python

import CDM
import sys
import json

if __name__ == '__main__':

    alias='ent'
    # username='seth.shaw@unlv.edu'
    # password='YUsPhXqe'
    # license='6WNYM-LH5KC-RJZMY-HZN65'
    ws_url='https://server17304.contentdm.oclc.org'
    # catcher_url='http://server17304.contentdm.oclc.org:8888/'
    queryClient = CDM.QueryClient(ws_url)
    # catcher = CDM.CatcherSession(catcher_url,username,password,license)
    # if not catcher.checkLogin():
    #     sys.exit("Could not connect to the catcher service.\n")
    query='0' # get every item
    fields = ['identi','object','title']
    for result in queryClient.query(alias,query,fields):


        print("\t".join(('ent/id/'+str(result['pointer']),result['identi'].strip(),result['object'].strip(),result['title'].strip())))
        # Update CDM and report
        # catcher.edit(alias, result['pointer'], 'date', new_date)
        # print("\t".join((str(result['pointer']),result['date'],new_date,json.dumps(catcher.transactions[-1]))))
