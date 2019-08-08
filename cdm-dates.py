#! /usr/bin/python

import CDM
import sys
import json

if __name__ == '__main__':

    alias='p17304coll4'
    username='seth.shaw@unlv.edu'
    password='YUsPhXqe'
    license='6WNYM-LH5KC-RJZMY-HZN65'
    ws_url='https://server17304.contentdm.oclc.org'
    catcher_url='http://server17304.contentdm.oclc.org:8888/'
    queryClient = CDM.QueryClient(ws_url)
    catcher = CDM.CatcherSession(catcher_url,username,password,license)
    if not catcher.checkLogin():
        sys.exit("Could not connect to the catcher service.\n")
    query='0' # get every item
    fields = ['title','date']
    for result in queryClient.query(alias,query,fields):
        # Skip records w/o dates or dates without '/'
        if not 'date' in result or '/' not in result['date']:
            continue
        # Parse the date and rejoin in YYYY-MM-DD format
        month,day,year = result['date'].split('/',2)
        new_date = '-'.join((year.zfill(4),month.zfill(2),day.zfill(2)))
        print("\t".join((str(result['pointer']),result['date'],new_date)))
        # Update CDM and report
        # catcher.edit(alias, result['pointer'], 'date', new_date)
        # print("\t".join((str(result['pointer']),result['date'],new_date,json.dumps(catcher.transactions[-1]))))
