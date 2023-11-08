import requests
from requests.auth import HTTPBasicAuth
import json
import pprint
import prometheus_client
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway,Info


vip="10.56.68.100"
username="admin"
password="Nutanix/4u$"
container_list="ctr2noebm3 testctr1"

prometheus_client.instance_ip_grouping_key()

#v1vipURL="https://"+vip+":9440/PrismGateway/services/rest/v1/vms/"

v1vipURL="https://10.56.68.100:9440/PrismGateway/services/rest/v1/vms/"
requests.packages.urllib3.disable_warnings()
try:
    response=requests.get(v1vipURL, auth=HTTPBasicAuth(username,password),verify=False)
    response.raise_for_status()
except requests.exceptions.HTTPError as err:
    raise SystemExit(err)

result=response.json()
entities=result["entities"]
registry = CollectorRegistry()


extra_info = Info('thisjob', 'Information about this batchjob run', registry=registry)
extra_info.info({'instance': "fake name"})

g = Gauge('per_vm_stats', 'VM stat', registry=registry,labelnames=['vmname','statname'])

#Do the per VM stats
for entity in entities:
    vmname=entity["vmName"]
    print(vmname)
    for stat_name in entity["stats"]:
         stat_value=entity["stats"][stat_name]
         print(stat_name,stat_value)
         g.labels(vmname,stat_name).set(stat_value)
    pprint.pprint(g)
    #Use grouping_key=prometheus_client.instance_ip_grouping_key() to set the instance key as the IP address
    #of the host where this python process is running.  Else we can set the dictionary to whatever we wamt

    #push_to_gateway('localhost:9091', job="thisjob", registry=registry,grouping_key=prometheus_client.instance_ip_grouping_key())
    #push_to_gateway('localhost:9091', job="thisjob", registry=registry,grouping_key={'instance': vip,"bogus":"true"})
    push_to_gateway('localhost:9091', job="thisjob", registry=registry,grouping_key={'instance': vip})

