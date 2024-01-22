import json
import requests
import pprint
from requests.auth import HTTPBasicAuth
import time
import os
import time
import sys
import argparse

#needed to make this work with Unix redirection/tee
sys.stdout.reconfigure(line_buffering=True)

parser=argparse.ArgumentParser()
parser.add_argument("-v","--vip",required=True,help="Name of IP of cluster VIP")
parser.add_argument("-c","--count",required=False,type=int,default=25,help="Number of vm entries to report")
parser.add_argument("-u","--user",required=False,default="admin",help="Prism username")
parser.add_argument("-p","--password",required=True,help="Prism password")
args=parser.parse_args()

def main():
    vip=args.vip
    username=args.user
    password=args.password
    vms_to_list=args.count
    v1vipURL="https://"+vip+":9440/PrismGateway/services/rest/v1/vms/"
    check_prism_accessible(vip)
    #exit()
    while True:
        requests.packages.urllib3.disable_warnings()
        # Time the API request response time
        t1=time.perf_counter()
        response=requests.get(v1vipURL, auth=HTTPBasicAuth(username,password),verify=False)
        t2=time.perf_counter()
        api_resp=t2-t1
        result=response.json()
        res=result["entities"]
        num_results=len(res)
        #Clear the terminal for top-like action.
        os.system('clear')
        #Print header and API response time
        print(f"API response time {api_resp:3.2f}s with {str(num_results):4} entries")
        print(f'{"vmname":>30} {"GB":>5} {"VCPU":>5} {"IOPS":>7} {"CPU%":>5} {"State":>5} {"BW MB/s":>9} {"BW-Read MB/s":>9} {"BW-Write MB/s":>9}')
        
        vmlist=sorted(res, key=lambda f: int(f['stats']["hypervisor_cpu_usage_ppm"]),reverse=True)
        count=1
        for i in range(0,len(vmlist)-1):
            vm=vmlist[i]
            # skip CVM and unhosted/powered off VMs
            if not vm["controllerVm"] and (vm["powerState"] == "on"):
                vm_total_bw_kbps=vm["stats"]["controller_io_bandwidth_kBps"]
                vm_total_bw_mbps=int(int(vm_total_bw_kbps)/1000)
                vm_total_read_bw_kbps=vm["stats"]["controller_read_io_bandwidth_kBps"]
                vm_total_read_bw_mbps=int(int(vm_total_read_bw_kbps)/1000)
                vm_total_write_bw_kbps=vm["stats"]["controller_write_io_bandwidth_kBps"]
                vm_total_write_bw_mbps=int(int(vm_total_write_bw_kbps)/1000)
                vm_powerstate=vm["powerState"] 
                vm_name=vm["vmName"]
                vm_vcpu=vm["numVCpus"]
                vm_mem_gb=int((int(vm["memoryCapacityInBytes"])/1024**3))
                vm_iops=vm["stats"]["controller_num_iops"]
                vm_cpu_pct=((int(vm["stats"]["hypervisor_cpu_usage_ppm"])/1000000)*100)
                print(f'{vm_name:>30.30} {vm_mem_gb:>5} {vm_vcpu:>5} {vm_iops:>7} {vm_cpu_pct:>5.2f} {vm_powerstate:>5} {vm_total_bw_mbps:>9} {vm_total_read_bw_mbps:>9} {vm_total_write_bw_mbps:>9}')
                count=count+1
            if (count>vms_to_list):
                break    
        time.sleep(10)

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


if __name__ == "__main__":
    main()
