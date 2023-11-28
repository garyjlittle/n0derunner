import requests
from requests.auth import HTTPBasicAuth
import json
import pprint
import prometheus_client
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway,Info
from prometheus_client import start_http_server, Summary
import time
import random

vip="10.56.68.100"
username="admin"
password="Nutanix/4u$"

prometheus_client.instance_ip_grouping_key()

v1vipURL="https://"+vip+":9440/PrismGateway/services/rest/v1/vms/"

#Gauges etc. must be instantiated before starting the http server
#they can be updata at any time afterwards...
g = Gauge('nutanix_v1_api', 'VM stat',labelnames=['vmname','statname'])
start_http_server(8000)

requests.packages.urllib3.disable_warnings()
while(True):
    try:
        response=requests.get(v1vipURL, auth=HTTPBasicAuth(username,password),verify=False)
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        raise SystemExit(err)

    result=response.json()
    entities=result["entities"]


    #Do the per VM stats
    for entity in entities:
        vmname=entity["vmName"]
        print(vmname)

        for stat_name in entity["stats"]:
            stat_value=entity["stats"][stat_name]
            print(vmname,stat_name,stat_value)
            #g.labels(vmname,stat_name).set(stat_value)
            gid=g.labels(vmname,stat_name)
            gid.set(stat_value)
        #Summary(job="vmstats", registry=registry,grouping_key={'instance': vip})
        #push_to_gateway('localhost:9091', job="vmstats", registry=registry,grouping_key={'instance': vip})
    time.sleep(5)

