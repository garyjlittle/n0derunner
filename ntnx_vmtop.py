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
parser.add_argument("--user",required=False,default="admin",help="Prism username")
parser.add_argument("--password",required=True,help="Prism password")
args=parser.parse_args()

vip=args.vip
username=args.user
password=args.password
vms_to_list=args.count

v1vipURL="https://"+vip+":9440/PrismGateway/services/rest/v1/vms/"

def main():
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
        print(f'{"vmname":>20} {"GB":>5} {"VCPU":>5} {"IOPS":>7} {"CPU%":>5} {"State":>5}')
        
        vmlist=sorted(res, key=lambda f: int(f['stats']["hypervisor_cpu_usage_ppm"]),reverse=True)
        count=1
        for i in range(0,len(vmlist)-1):
            vm=vmlist[i]
            # skip CVM and unhosted/powered off VMs
            if not vm["controllerVm"] and (vm["powerState"] == "on"):
                vm_powerstate=vm["powerState"] 
                vm_name=vm["vmName"]
                vm_vcpu=vm["numVCpus"]
                vm_mem_gb=int((int(vm["memoryCapacityInBytes"])/1024**3))
                vm_iops=vm["stats"]["controller_num_iops"]
                vm_cpu_pct=((int(vm["stats"]["hypervisor_cpu_usage_ppm"])/1000000)*100)
                print(f'{vm_name:>20.20} {vm_mem_gb:>5} {vm_vcpu:>5} {vm_iops:>7} {vm_cpu_pct:>5.2f} {vm_powerstate:>5} ')
                count=count+1
            if (count>vms_to_list):
                break    
        time.sleep(10)

if __name__ == "__main__":
    main()
