import requests
from requests.auth import HTTPBasicAuth
import json
import pprint
import prometheus_client
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway,Info
from prometheus_client import start_http_server, Summary
import time
import random
import argparse
import os


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("-v","--vip",action="store",help="The Virtual IP for the cluster",default=os.environ.get("VIP"))
    parser.add_argument("-u","--username",action="store",help="The prism username",default=os.environ.get("PRISMUSER"))
    parser.add_argument("-p","--password",action="store",help="The prism password",default=os.environ.get("PRISMPASS"))
    args=parser.parse_args()
    vip=args.vip
    username=args.username
    password=args.password
    process_stats(vip,username,password)

    

def process_stats(vip,username,password):
    #Gauges etc. must be instantiated before starting the http server
    #they can be updata at any time afterwards...
    prometheus_client.instance_ip_grouping_key()
    g = Gauge('nutanix_v1_api', 'VM stat',labelnames=['vmname','statname'])
    start_http_server(8000)

    requests.packages.urllib3.disable_warnings()
    v1vipURL="https://"+vip+":9440/PrismGateway/services/rest/v1/vms/"
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

if __name__ == '__main__':
    main()