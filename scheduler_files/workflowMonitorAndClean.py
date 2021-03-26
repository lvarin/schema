#!/usr/bin/python3
####################################################################################
#
#  Copyright (c) 2018 Thanasis Vergoulis & Konstantinos Zagganas &  Loukas Kavouras
#  for the Information Management Systems Institute, "Athena" Research Center.
#  
#  This file is part of SCHeMa.
#  
#  SCHeMa is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  
#  SCHeMa is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with Foobar.  If not, see <https://www.gnu.org/licenses/>.
#
####################################################################################
import requests
import sys
import os
import json
import psycopg2 as psg
import time
import subprocess
import shutil
import urllib.request
from contextlib import closing

configFileName=os.path.dirname(os.path.abspath(__file__)) + '/configuration.json'
configFile=open(configFileName,'r')
config=json.load(configFile)
configFile.close()

db=config['database']
host=db['host']
dbuser=db['username']
passwd=db['password']
dbname=db['database']
ftp=config['localftp']
ftpuser=ftp['username']
ftppass=ftp['password']
ftpdomain=ftp['domain']

jobid=sys.argv[1]
wesEndpoint=sys.argv[2]
teskEndpoint=sys.argv[3]
outFolder=sys.argv[4]
logPath=sys.argv[5]

workflowUrl=wesEndpoint + '/ga4gh/wes/v1/runs/' + jobid

headers={'Accept':'application/json', 'Content-Type': 'application/json'}
response = requests.get(workflowUrl,headers=headers)

body=json.loads(response.content)
status=body['state']

while (status!='COMPLETE') and (status!='EXECUTOR_ERROR') and (status!='CANCELED'):
    time.sleep(5)
    response = requests.get(workflowUrl,headers=headers)
    body=json.loads(response.content)
    status=body['state']

runLog=body['run_log']
taskLogs=body['task_logs']
outputs=body['outputs']

start=runLog['task_started']

if (status=='EXECUTOR_ERROR'):
    sql="UPDATE run_history SET start='" + start +  "', stop=NOW(), status='Error' WHERE jobid='" + jobid + "'"
elif (status=='CANCELED'):
    sql="UPDATE run_history SET start='" + start +  "', stop=NOW(), status='Canceled' WHERE jobid='" + jobid + "'"
elif (status=='COMPLETE'):
    stop=runLog['task_finished']
    ram=0.0;
    cpu=0.0
    taskIds={}
    i=1
    taskSteps={}

    #for each task collect its info
    #clean up tesk jobs after keeping their logs
    for log in taskLogs:
        resources=log['resources']
        cpu+=float(resources['cpu_cores'])
        ram+=float(resources['ram_gb'])
        taskIds[log['id']]=log['name']
        taskSteps[i]=log['id']
        i+=1
    
    ram/=len(taskLogs);
    cpu/=len(taskLogs);
    sql="UPDATE run_history SET start='" + start +  "', stop='" + stop + "', status='Complete', ram=" + str(ram) + ",cpu=" + str(cpu) +  "WHERE jobid='" + jobid + "'"
else:
    sql="UPDATE run_history SET status='%s' WHERE jobid='%s'" % (status, jobid)

conn=psg.connect(host=host, user=dbuser, password=passwd, dbname=dbname)
cur=conn.cursor()
cur.execute(sql)
conn.commit()
conn.close()


if (status=='COMPLETE' or status=='EXECUTOR_ERROR'):
    logfile=logPath + '/' + 'logs.txt'
    g=open(logfile,'w')
    
    g.write('>>STDERR\n')
    try:
        g.write(body['run_log']['stderr']+ '\n')
    except KeyError as kerr:
        g.write("NO LOG\n")

    g.write('>>STDOUT\n')
    try:
        g.write(body['run_log']['stdout'] + '\n')
    except KeyError as kerr:
        g.write("NO LOG\n")

    g.close()


if (status=='COMPLETE'):
    #write logs

    #retrieve workflow outputs
    for output in outputs:
        if (isinstance(outputs[output],list)):
            for subOutput in outputs[output]:
                outClass=subOutput['class']
                name=subOutput['basename']
                url=subOutput['location']
                localpath=outFolder + '/' + name
                if outClass=='File':
                    url=url.replace('ftp://' + ftpdomain, 'ftp://' + ftpuser + ':' + ftppass + '@' + ftpdomain + '/')
                    #this closes the open handle after the block is done
                    with closing(urllib.request.urlopen(url)) as r:
                        with open(localpath, 'wb') as f:
                            shutil.copyfileobj(r, f)
        else:
            outClass=outputs[output]['class']
            name=outputs[output]['basename']
            url=outputs[output]['location']
            localpath=outFolder + '/' + name
            if outClass=='File':
                url=url.replace('ftp://' + ftpdomain, 'ftp://' + ftpuser + ':' + ftppass + '@' + ftpdomain + '/')
                #this closes the open handle after the block is done
                with closing(urllib.request.urlopen(url)) as r:
                    with open(localpath, 'wb') as f:
                        shutil.copyfileobj(r, f)

