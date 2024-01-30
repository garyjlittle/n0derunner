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
    if not (vip and username and password):
        print("Need a vip, username and password")
        exit(1)
    
    check_prism_accessible(vip)
    process_stats(vip,username,password)


def process_stats(vip,username,password):
    container_stats_list=load_defined_stats("container-api-stats-config.txt")
    vm_stats_list=load_defined_stats("vm-api-stats-config.txt")

    collect_vm_stats=True
    collect_host_stats=False
    collect_container_stats=False

    use_method=False
    
    #Attempt to fileter spurious respnse time values for very low IO rates
    filter_spurious_response_times=True
    spurious_iops_threshold=50

    #Gauges etc. must be instantiated before starting the http server
    #they can be updata at any time afterwards...
    prometheus_client.instance_ip_grouping_key()
    gVM = Gauge('v1_stat_vm', 'VM stat',labelnames=['vmname','statname'])
    gHOST = Gauge('v1_stat_host', 'VM stat',labelnames=['hostname','statname'])
    gCTR = Gauge('v1_stat_container', 'VM stat',labelnames=['container','statname'])

    # Need to start the "prometheus" http server after the Gauges are instantiated
    start_http_server(8000)

    requests.packages.urllib3.disable_warnings()
    v1_stat_VM_URL="https://"+vip+":9440/PrismGateway/services/rest/v1/vms/"
    v1_stat_HOST_URL="https://"+vip+":9440/PrismGateway/services/rest/v1/hosts/"
    v1_stat_CTR_URL="https://"+vip+":9440/PrismGateway/services/rest/v1/containers/"


    while(True):
        try:
            vm_response=requests.get(v1_stat_VM_URL, auth=HTTPBasicAuth(username,password),verify=False)
            vm_response.raise_for_status()
            host_response=requests.get(v1_stat_HOST_URL, auth=HTTPBasicAuth(username,password),verify=False)
            host_response.raise_for_status()
            ctr_response=requests.get(v1_stat_CTR_URL, auth=HTTPBasicAuth(username,password),verify=False)
            ctr_response.raise_for_status()            
        except requests.exceptions.HTTPError as err:
            raise SystemExit(err)

        vm_result=vm_response.json()
        vm_entities=vm_result["entities"]

        host_result=host_response.json()
        host_entities=host_result["entities"]

        ctr_result=ctr_response.json()
        ctr_entities=ctr_result["entities"]

        #Do the per VM stats
        if collect_vm_stats:
            for entity in vm_entities:
                vmname=entity["vmName"]
                print(vmname)

                for stat_name in entity["stats"]:
                    if use_method:
                        if stat_name in vm_stats_list:
                            stat_value=entity["stats"][stat_name]
                            print(vmname,stat_name,stat_value)
                            #g.labels(vmname,stat_name).set(stat_value)
                            gid=gVM.labels(vmname,stat_name)
                            gid.set(stat_value)
                    else:
                        stat_value=entity["stats"][stat_name]
                        print(vmname,stat_name,stat_value)
                        #g.labels(vmname,stat_name).set(stat_value)
                        gid=gVM.labels(vmname,stat_name)
                        gid.set(stat_value)
                #Summary(job="vmstats", registry=registry,grouping_key={'instance': vip})
                #push_to_gateway('localhost:9091', job="vmstats", registry=registry,grouping_key={'instance': vip})
                
        #Do the per Host stats
        if collect_host_stats:
            for entity in host_entities:
                #pprint.pprint(entity)
                #exit()
                hostname=entity["name"]
                print("hostname=",hostname)

                for stat_name in entity["stats"]:
                    stat_value=entity["stats"][stat_name]
                    print(hostname,stat_name,stat_value)
                    #g.labels(vmname,stat_name).set(stat_value)
                    gid=gHOST.labels(hostname,stat_name)
                    gid.set(stat_value)

        #Maybe collect per Container storage stats
        if collect_container_stats:
            #gather_container_stats(ctr_entities,use_method,container_stats_list,gCTR,filter_spurious_response_times,spurious_iops_threshold)
            #Do Generic
            #gather_container_stats(ctr_entities,use_method,container_stats_list,gCTR,filter_spurious_response_times,spurious_iops_threshold)
            gather_ceneric_storage_stats(ctr_entities,use_method,container_stats_list,gCTR,filter_spurious_response_times,spurious_iops_threshold)
        #Maybe collect per VM stats
        #if collect_vm_stats:
            #gather_ceneric_storage_stats(vm_entities,use_method,vm_stats_list,gVM,filter_spurious_response_times,spurious_iops_threshold)


        time.sleep(1)

def gather_ceneric_storage_stats(ctr_entities,use_method,stats_list,gCTR,filter_spurious_response_times,spurious_iops_threshold):                             
    for entity in ctr_entities:
            #pprint.pprint(entity)
            #exit()
            entity_name=entity["name"]
            print("container=",entity_name)

            for stat_name in entity["stats"]:
                if use_method:
                    if stat_name in stats_list:
                        stat_value=entity["stats"][stat_name]
                        print(entity_name,stat_name,stat_value)
                        #g.labels(vmname,stat_name).set(stat_value)
                        gid=gCTR.labels(entity_name,stat_name)
                        gid.set(stat_value)
                else:
                        stat_value=entity["stats"][stat_name]
                        print(entity_name,stat_name,stat_value)
                        #g.labels(vmname,stat_name).set(stat_value)
                        gid=gCTR.labels(entity_name,stat_name)
                        gid.set(stat_value)
            if filter_spurious_response_times:
                print("Supressing spurious values")
                read_rate_iops=entity["stats"]["controller_num_read_iops"]
                write_rate_iops=entity["stats"]["controller_num_write_iops"]

                if (int(read_rate_iops)<spurious_iops_threshold):
                    print("read iops too low, supressing write response times")
                    gid=gCTR.labels(entity_name,"controller_avg_read_io_latency_usecs")
                    gid.set("0")
                if (int(write_rate_iops)<spurious_iops_threshold):
                    print("write iops too low, supressing write response times")
                    gid=gCTR.labels(entity_name,"controller_avg_write_io_latency_usecs")
                    gid.set("0")

def gather_container_stats(ctr_entities,use_method,container_stats_list,gCTR,filter_spurious_response_times,spurious_iops_threshold):                             
    for entity in ctr_entities:
            #pprint.pprint(entity)
            #exit()
            entity_name=entity["name"]
            print("container=",entity_name)

            for stat_name in entity["stats"]:
                if use_method:
                    if stat_name in container_stats_list:
                        stat_value=entity["stats"][stat_name]
                        print(entity_name,stat_name,stat_value)
                        #g.labels(vmname,stat_name).set(stat_value)
                        gid=gCTR.labels(entity_name,stat_name)
                        gid.set(stat_value)
                else:
                        stat_value=entity["stats"][stat_name]
                        print(entity_name,stat_name,stat_value)
                        #g.labels(vmname,stat_name).set(stat_value)
                        gid=gCTR.labels(entity_name,stat_name)
                        gid.set(stat_value)
            if filter_spurious_response_times:
                print("Supressing spurious values")
                read_rate_iops=entity["stats"]["controller_num_read_iops"]
                write_rate_iops=entity["stats"]["controller_num_write_iops"]

                if (int(read_rate_iops)<spurious_iops_threshold):
                    print("read iops too low, supressing write response times")
                    gid=gCTR.labels(entity_name,"controller_avg_read_io_latency_usecs")
                    gid.set("0")
                if (int(write_rate_iops)<spurious_iops_threshold):
                    print("write iops too low, supressing write response times")
                    gid=gCTR.labels(entity_name,"controller_avg_write_io_latency_usecs")
                    gid.set("0")


                    



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
    print("URL OK")
    return url, status, message
    requests.packages.urllib3.disable_warnings()
    url="http://"+vip
    try:
        page = requests.get(url,verify=False,timeout=5)
        print(page.status_code)
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError):
        print("Error URL is unreachable")
        exit(1)

def load_defined_stats(filename):
    defined_stats=[]
    with open(filename) as f:
        for line in f:
            defined_stats.append(line.strip())
    return defined_stats

if __name__ == '__main__':
    main()