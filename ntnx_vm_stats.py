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

global collect_container_stats,collect_host_stats,collect_vm_stats,use_method,curated,filter_spurious_response_times,spurious_iops_threshold

collect_vm_stats=True
collect_host_stats=True
collect_container_stats=True
#Attempt to fileter spurious respnse time values for very low IO rates
filter_spurious_response_times=True
spurious_iops_threshold=50
            
restrict_counter_set=True
# Counter Centric groups the stats by counter (e.g. read iops, resposnse times) - entities are labels
# Entity Centric groups the stats by entities (e.g. vms, containers, hosts) - counters are labels
# Counter centric is always restricted
counter_centric=True
entity_centric=True


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
    setup_prometheus_endpoint_counter_centric()
    setup_prometheus_endpoint_entity_centric()
    #Start prometheus end-point
    start_http_server(8000)


    while(True):
        if counter_centric:
            #Metric/Counter Centric, entites are labels
                for family in ["containers","vms","hosts","clusters"]:
                    entities=get_family_from_api(vip,family)
                    push_counter_centric_to_prometheus(family,entities)

        if entity_centric:
            #Entity Centric.  Metrics/Counters are labels
                for family in ["containers","vms","hosts","clusters"]:
                    entities=get_family_from_api(vip,family)
                    push_entity_centric_to_prometheus(family,entities)
        time.sleep(1)

#-----------
# END Main
#------------
        
def push_counter_centric_to_prometheus(family,entities):
    print("incoming family is ",family)
    #For each thing in the family
    print("family is",family)
    for entity in entities:
        # for each thing of type family
        if family == "containers":
            entity_name=(entity["name"])
        if family == "vms":
            entity_name=(entity["vmName"])
        if family == "hosts":
            entity_name=(entity["name"])
        if family == "clusters":
            entity_name=(entity["name"])
        
        gIOPSRead.labels(family,entity_name).set(entity["stats"]["controller_num_read_iops"])
        gIOPSWrite.labels(family,entity_name).set(entity["stats"]["controller_num_write_iops"])
        gIOPSRW.labels(family,entity_name).set(entity["stats"]["controller_num_iops"])
        gTPUTRead.labels(family,entity_name).set(entity["stats"]["controller_read_io_bandwidth_kBps"])
        gTPUTWrite.labels(family,entity_name).set(entity["stats"]["controller_write_io_bandwidth_kBps"])
        gTPUTRW.labels(family,entity_name).set(entity["stats"]["controller_io_bandwidth_kBps"])
        gRWResp.labels(family,entity_name).set(entity["stats"]["controller_avg_io_latency_usecs"])
        gREADResp.labels(family,entity_name).set(entity["stats"]["controller_avg_read_io_latency_usecs"])
        gWRITEResp.labels(family,entity_name).set(entity["stats"]["controller_avg_write_io_latency_usecs"])

        #Maybe overwrite response times with -1 if the rates fall below the spurious IO threshold
        if filter_spurious_response_times:
            read_rate_iops=entity["stats"]["controller_num_read_iops"]
            write_rate_iops=entity["stats"]["controller_num_write_iops"]
            if (int(read_rate_iops)<spurious_iops_threshold):
                print("Supressing spurious read resp for ",entity_name)
                gREADResp.labels(family,entity_name).set(-1)
          
            if (int(write_rate_iops)<spurious_iops_threshold):
                print("Supressing spurious write resp for ",entity_name)
                gWRITEResp.labels(family,entity_name).set(-1)

            if int(write_rate_iops)+int(read_rate_iops)<spurious_iops_threshold:
                print("Supressing spurious R/W resp for ",entity_name)
                gRWResp.labels(family,entity_name).set(-1)
    



        #
        # Do CPU Utilization for Hosts and VMs
        #
        if family in ["vms","hosts"]:
            if family == "vms":
                    #CPU Ready is only applicable to VMs running on a Hypervisor, not the host itself
                    gCPU_READY.labels(family,entity_name).set(entity["stats"]["hypervisor.cpu_ready_time_ppm"])
            gCPU_UTIL.labels(family,entity_name).set(entity["stats"]["hypervisor_cpu_usage_ppm"])

def get_family_from_api(vip,family):
    requests.packages.urllib3.disable_warnings()
    v1_stat_VM_URL="https://"+vip+":9440/PrismGateway/services/rest/v1/"+family+"/"
    response=requests.get(v1_stat_VM_URL, auth=HTTPBasicAuth(username,password),verify=False)
    response.raise_for_status()
    result=response.json()
    entities=result["entities"]
    return entities

def setup_prometheus_endpoint_entity_centric():
    print("Setup Prometheus Endpoint")
    #
    # Setup gauges for VMs Hosts and Containers
    #
    global gVM,gHOST,gCTR,gCLUSTER
    prometheus_client.instance_ip_grouping_key()
    gVM = Gauge('vm_stats', 'Stats grouped by VM',labelnames=['vmname','statname'])
    gHOST = Gauge('host_stats', 'Stats grouped by Pysical Host',labelnames=['hostname','statname'])
    gCTR = Gauge('container_stats', 'Stats grouped by Storage Container',labelnames=['container','statname'])
    gCLUSTER = Gauge('cluster_stats','Stats grouped by cluster',labelnames=['clustername','statname'])
    # Need to start the "prometheus" http server after the Gauges are instantiated

def setup_prometheus_endpoint_counter_centric():
    #
    # Setup guages for IOPS, Throughput and CPU Utilization
    #
    global gIOPSRead,gIOPSWrite,gIOPSRW,gTPUTRead,gTPUTWrite,gTPUTRW,gREADResp,gWRITEResp,gRWResp,gCPU_UTIL,gCPU_READY
    prometheus_client.instance_ip_grouping_key()
    gIOPSRead = Gauge('Read_IOPS','Read IOPS IOs Per Second',labelnames=['aggregation','identifier'])
    gIOPSWrite = Gauge('Write_IOPS','Write IOPS IOs Per Second',labelnames=['aggregation','identifier'])
    gIOPSRW = Gauge('Read_Write_IOPS','Combined Read and Write IOPS IOs Per Second',labelnames=['aggregation','identifier'])
    gTPUTRead = Gauge('Read_TPUT','Read Throughput in KB/s',labelnames=['aggregation','identifier'])
    gTPUTWrite = Gauge('Write_TPUT','Write Throughput in KB/s',labelnames=['aggregation','identifier'])
    gTPUTRW = Gauge('ReadWrite_TPUT','Combined Read and Write Throughput in KB/s',labelnames=['aggregation','identifier'])
    gREADResp = Gauge('Read_Response_Time',"Read IO Response time (Latency)",labelnames=['aggregation','identifier'])
    gWRITEResp = Gauge('Write_Response_Time',"Write IO Response time (Latency)",labelnames=['aggregation','identifier'])
    gRWResp = Gauge('Read_Write_Response_Time',"Combined Read/Write IO Response time (Latency)",labelnames=['aggregation','identifier'])
    gCPU_UTIL = Gauge('CPU_Utilization_ppm',"CPU Utilization expressed as parts per million",labelnames=['aggregation','identifier'])
    gCPU_READY = Gauge('CPU_Ready_ppm',"CPU Ready Time expressed as parts per million",labelnames=['aggregation','identifier'])

    # Need to start the "prometheus" http server after the Gauges are instantiated

def push_entity_centric_to_prometheus(family,entities):

    stats_list=load_defined_stats("entity-centric-stats.txt")

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
            for stat_name in entity["stats"]:
                if restrict_counter_set:
                    #If we are using a restricted set, only create
                    #gauges for the named stats placed in the config
                    #array "stats_list" which is populated in "load_defined_stats"
                    if stat_name in stats_list:
                        stat_value=entity["stats"][stat_name]
                        print(entity_name,stat_name,stat_value)
                        gid=gGAUGE.labels(entity_name,stat_name)
                        gid.set(stat_value)
                else:
                        stat_value=entity["stats"][stat_name]
                        print(entity_name,stat_name,stat_value)
                        gid=gGAUGE.labels(entity_name,stat_name)
                        gid.set(stat_value)
            #Overwrite if falling below spurious IO rate threshold
            if filter_spurious_response_times:
                print("Supressing spurious values")
                read_rate_iops=entity["stats"]["controller_num_read_iops"]
                write_rate_iops=entity["stats"]["controller_num_write_iops"]

                if (int(read_rate_iops)<spurious_iops_threshold):
                    print("read iops too low, supressing write response times")
                    gGAUGE.labels(entity_name,"controller_avg_read_io_latency_usecs").set("-1")
                if (int(write_rate_iops)<spurious_iops_threshold):
                    print("write iops too low, supressing write response times")
                    gGAUGE.labels(entity_name,"controller_avg_write_io_latency_usecs").set("-1")
                if (int(write_rate_iops)+int(read_rate_iops)<spurious_iops_threshold):
                    gGAUGE.labels(entity_name,"controller_avg_read_io_latency_usecs").set("-1")


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

#Not currently used - for future use to setup the various
#Metric centric gauges via configuration file (json)
def load_defined_stats_json(filename):
    defined_stats=[]
    f=open(filename)

    res=json.load(f)
    pprint.pprint(res)
    print("keys")
    key=list(res.keys())
    pprint.pprint(list(key)[0])
    print("keys done")
    inner=res["container_stats"]

    for tup in inner:
        if "controller_num_iops" in tup.values():
            defined_stats.append(tup["name"])
            #print(tup["type"])
            #print(tup["description"])
            continue
    return defined_stats

def load_defined_stats(filename):
    defined_stats=[]
    with open(filename) as f:
        for line in f:
            defined_stats.append(line.strip())
    return defined_stats

if __name__ == '__main__':
    main()