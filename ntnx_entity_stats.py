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

global filter_spurious_response_times,spurious_iops_threshold

#Attempt to filter spurious respnse time values for very low IO rates
filter_spurious_response_times=True
spurious_iops_threshold=50
            
# Entity Centric groups the stats by entities (e.g. vms, containers, hosts) - counters are labels
def main():
    global username,password
    parser=argparse.ArgumentParser()
    parser.add_argument("-v","--vip",action="store",help="The Virtual IP for the cluster",default=os.environ.get("VIP"))
    parser.add_argument("-u","--username",action="store",help="The prism username",default=os.environ.get("PRISMUSER"))
    parser.add_argument("-p","--password",action="store",help="The prism password",default=os.environ.get("PRISMPASS"))
    args=parser.parse_args()
    vip=args.vip
    username=args.username
    password=args.password
    if not (vip and username and password):
        print("Need a vip, username and password")
        exit(1)
    
    check_prism_accessible(vip)
    #Instantiate the prometheus guages to store metrics
    setup_prometheus_endpoint_entity_centric()
    #Start prometheus end-point on port 8000 after the Gauges are instantiated        
    start_http_server(8000)

    #Loop forever getting the metrics for all available entities (They may come and go)
    #then expose the metrics for those entities on prometheus exporter ready for scraping
    while(True):
        for family in ["containers","vms","hosts","clusters"]:
            entities=get_entity_names(vip,family)
            push_entity_centric_to_prometheus(family,entities)
        #The counters are meant for trending and are quite coarse
        #10s of  seconds is a reasonable scrape interval    
        time.sleep(10)

def setup_prometheus_endpoint_entity_centric():
    #
    # Setup gauges for VMs Hosts and Containers
    #
    global gVM,gHOST,gCTR,gCLUSTER
    prometheus_client.instance_ip_grouping_key()
    gVM = Gauge('vms', 'Stats grouped by VM',labelnames=['vm_name','metric_name'])
    gHOST = Gauge('hosts', 'Stats grouped by Pysical Host',labelnames=['host_name','metric_name'])
    gCTR = Gauge('containers', 'Stats grouped by Storage Container',labelnames=['container_name','metric_name'])
    gCLUSTER = Gauge('cluster','Stats grouped by cluster',labelnames=['cluster_name','metric_name'])


def push_entity_centric_to_prometheus(family,entities):

    if family == "vms":
        gGAUGE=gVM
    if family == "containers":
        gGAUGE=gCTR
    if family == "hosts":
        gGAUGE=gHOST
    if family == "clusters":
        gGAUGE=gCLUSTER
    
     #Get data from the dictionary passed in and set the gauges
    for entity in entities:
            #Each family may use a different identifier for the entity name.
            if family == "containers":
                entity_name=entity["name"]
            if family == "vms":
                entity_name=entity["vmName"]
            if family == "hosts":
                entity_name=entity["name"]
            if family == "clusters":
                entity_name=entity["name"]
            # regardless of the family, the stats are always stored in a  
            # structure called stats.  Within the stats structure the data 
            # is layed out as Key:Value.  We just walk through make a prometheus
            # guage for whatever we find
            for metric_name in entity["stats"]:
                stat_value=entity["stats"][metric_name]
                if any(prefix in metric_name for prefix in ["controller","hypervisor","guest"]):
                    print(entity_name,metric_name,stat_value)
                    gid=gGAUGE.labels(entity_name,metric_name)
                    gid.set(stat_value)
            #Overwrite value with -1 if IO rate is below spurious IO rate threshold.  This is 
            #to avoid misleading response times for entities that are doing very little IO
            if filter_spurious_response_times:
                print("Supressing spurious values - entity centric - family",entity_name,family)
                read_rate_iops=entity["stats"]["controller_num_read_iops"]
                write_rate_iops=entity["stats"]["controller_num_write_iops"]
                rw_rate_iops=entity["stats"]["controller_num_iops"]

                if (int(read_rate_iops)<spurious_iops_threshold):
                    print("read iops too low, supressing write response times")
                    gGAUGE.labels(entity_name,"controller_avg_read_io_latency_usecs").set("-1")
                if (int(write_rate_iops)<spurious_iops_threshold):
                    print("write iops too low, supressing write response times")
                    gGAUGE.labels(entity_name,"controller_avg_write_io_latency_usecs").set("-1")
                if (int(rw_rate_iops)<spurious_iops_threshold):
                    print("RW iops too low, supressing write response times")
                    gGAUGE.labels(entity_name,"controller_avg_io_latency_usecs").set("-1")

def get_entity_names(vip,family):
    requests.packages.urllib3.disable_warnings()
    v1_stat_VM_URL="https://"+vip+":9440/PrismGateway/services/rest/v1/"+family+"/"
    response=requests.get(v1_stat_VM_URL, auth=HTTPBasicAuth(username,password),verify=False)
    response.raise_for_status()
    result=response.json()
    entities=result["entities"]
    return entities

def check_prism_accessible(vip):
    #Check name resolution
    url="http://"+vip

    status = None
    message = ''
    try:
        resp = requests.head('http://' + vip)   
        status = str(resp.status_code)
    except:
        if ("[Errno 11001] getaddrinfo failed" in str(vip) or     # Windows
            "[Errno -2] Name or service not known" in str(vip) or # Linux
            "[Errno 8] nodename nor servname " in str(vip)):      # OS X
            message = 'DNSLookupError'
        else:
            raise
    return url, status, message

if __name__ == '__main__':
    main()
