# Managing a Nutanix Cluster with Python and the V4 API
When the world was simpler, ssh and bash scripts were fine to manage infrastructure. Today we need a better set of tools to manage operations involving thousands of VMs.   A combination of Python and the Nutanix V4 API gives us a simple but powerful toolset to do sysadmin robustly at scale while maintining the simple elegance of bash/ssh/sed/awk and all our old friends.

![Link](https://github.com/garyjlittle/n0derunner/blob/b59811fb79d2a07be52118a6fe2e3faa1d5d55d0/screenshots/Developers-nutanix-com-annnotated.png)
##### Official V4 API Documentation
* [V4.0 **virtual machine APIs**](https://developers.nutanix.com/api-reference?namespace=vmm&version=v4.0)
* [V4.0 **cluster API**](https://developers.nutanix.com/api-reference?namespace=clustermgmt&version=v4.0)

* [Top level API Documentation](https://developers.nutanix.com/)
* [Python SDK Documentation](https://developers.nutanix.com/sdk-reference?namespace=vmm&version=v4.1&language=python)


## The two flavors of Python API
There are two ways that we can access the V4 API using python.

1. The native python way using using the Python `requests` libary
2. Using the Nutanix Python SDK `ntnx_vmm_py_client`

Each has its own benefits and really it comes down to  personal preference or convention.

* Using the REST API will already be familiar to anyone using other REST based APIs and you can use tools like [postman](#postman) to build your rest queries, explore the responses, look into the headers etc.
* Using the Python SDK gives a Pythonic Object oriented interface and manages things like sessions for you.  You can use IPython notebooks or modern IDE's like [VScode](#vscode) to explore the SDK and the objects returned via the API.

###### REST Calls
* Use the `requests` library to call up the API e.g. `response = requests.get(url, auth=(username, password), headers=headers, verify=False)`
* Convert the response from json into python arrays/dicts `vms = (response.json())`
* Access the elements using array/dict `name=vm['name']`
###### SDK Calls
* Import the `ntnx_vmm_py_client` to all up the API e.g. `vmlist=vm_api_instance.list_vms(_limit=limit, _page=page)`
* Access the elements as a python object `name=vm.name`

## Examples
##### Python REST Example
The REST API returns data in the usual way with JSON - the format is camelCase.  To see what data we can get back from the API - use the API documentation (linked above) - look for the command you want, find the URL of the function you want to call then look at the Respnse Samples (200 for successful response).  Most of the time the actual items of interest are in the `data` field, which is normally collapsed.  In the case of the `List VMs` api call `https://{pc-ip}:9440/api/vmm/v4.0/ahv/config/vms` the response looks something like this.
```
"data": 
[{
    "tenantId": "58c42276-2fd7-49bc-9bf7-67d18ba54f14",
    "extId": "6c335c2e-8b41-4973-b7d4-08fefbe88680",
    "links": 
[],
"name": "Test VM",
"description": "Description for your VM",
"createTime": "2009-09-23T14:30:00-07:00",
"updateTime": "2009-09-23T14:30:00-07:00",
"source": 
{},
"numSockets": 24,
"numCoresPerSocket": 40,   <--- fields are in camelCase
"numThreadsPerCore": 37,
"numNumaNodes": 16,
```
The 'data' element of the  response contains a json array with each element of the array containing information about a speficic VM represented as a json object which gets converted to a python dictionary when we call `response.json()`.  Here's an example of how to retrieve that data.  Assuming that the values of pc_vip, username, password are setup elsewhere and the required libraries are imported.
###### Import some libraries
```
import requests
import urllib3
import json
# set the PC IP, username, password etc.
```
###### Connect to the API and grab some data about the cluster VMs
```
def get_vm_list(pc_vip,username,password):
	url = f"https://{pc_vip}:9440/api/vmm/v4.0/ahv/config/vms"
	limit=100
	vm_list = []	
	# Loop to handle pagination	
	for page in range(0, 99999):
		headers = {'Content-Type': 'application/json'}
		url = f"https://{pc_vip}:9440/api/vmm/v4.0/ahv/config/vms?"
		url += (f"&$page={page}&$limit={limit}")
		response = requests.get(url, auth=(username, password), headers=headers, verify=False)
		if response.status_code == 200:
			vms = (response.json())
			headers = response.headers
			vm_list.extend(vms['data'])
			if len(vms['data']) < limit:
				print(f"Page {page} retrieved with {len(vms['data'])} VMs")
				break
			else:
				print(f"Page {page} retrieved with {len(vms['data'])} VMs")
		else:
			print(f"Failed to retrieve VM list: {response.status_code} - {response.text}")
			return None	
	return vm_list
```
Then you can iterate over the list and print out any details that are returned
```
vms= get_vm_list(pc_vip, user, password)
for vm in vms:
	extId=vm['extId']
	name=vm['name']
	print(f"VM Name: {name} - Ext ID: {extId}")
```
For my cluster with a bunch of X-ray VMs running on it, I get output that looks like this
```
VM Name: __curie_test_1751038395539_VDI_0000 - Ext ID: 85a746ac-84a2-4c75-b0af-dce3463e744a
VM Name: __curie_test_1751038395539_VDI_0005 - Ext ID: 7f3a5aa6-8be6-4dc3-a5d3-083c7e53339d
VM Name: __curie_test_1751038395539_VDI_0004 - Ext ID: 94cb3a13-066f-4ac2-895c-086d0a56be85
VM Name: __curie_test_1751038395539_VDI_0007 - Ext ID: 8bcadea9-57a0-45d6-a36b-4b3978332b66
VM Name: __curie_test_1751038395539_VDI_0006 - Ext ID: 1c62d6ea-e665-4993-9ad8-e0c8698a1051
VM Name: __curie_test_1751038395539_VDI_0001 - Ext ID: 755525dd-db94-4000-b525-e90cf0fb0bd8
VM Name: __curie_test_1751038395539_VDI_0003 - Ext ID: f70780d3-e7d4-4ed8-8a4a-c75c04caf65c
```
##### Python SDK Example
The SDK uses a different naming format for the function calls/methods and for data returned by the API.  [The API documentation can be used to find the required method](https://developers.nutanix.com/sdk-reference?namespace=vmm&version=v4.0&language=python), or by clicking on the **"Python Request Samples"** example.  For the response fields, it uses lowercase everywhere and `_` to separate words. e.g.  Since the object naming format is not the same as JSON tools like Postman are not that useful when using the SDK, but since the SDK returns a python object - [modern IDE's](#vscode) will be able to help when inspecting the contents of the object.  IPython notebooks are useful for this as is the debugger in vscode.  Unfortunately the API documentation only shows the response contents in REST format - not the SDK format, which is a bit annoying.
###### The VM list Python Request Sample
```
    try:
        api_response = vm_api.list_vms(_page=page, _limit=limit)
        print(api_response)
    except ntnx_vmm_py_client.rest.ApiException as e:
        print(e)
```
###### Object format
To get the first IP address of a given vm we can use this sort of notation.
```
vm.nics[0].network_info.ipv4_config.ip_address.value
```
Same example as above using SDK instead of REST
###### Setup the SDK instance
```
import ntnx_vmm_py_client
from ntnx_vmm_py_client import Configuration as VMMConfiguration
from ntnx_vmm_py_client import ApiClient as VMMClient
# setup the PC IP, username, password etc.
config = VMMConfiguration()
config.host = prism_central_ip_address
config.username = prism_central_username
config.password = prism_central_password
config.verify_ssl = False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
api_client = VMMClient(configuration=config)
vm_api_instance = ntnx_vmm_py_client.api.VmApi(api_client=api_client)
```
###### Use the SDK in a function
```
def get_vm_list_sdk():
	my_vms=[]
	vms_retrieved=0
	page=0
	count=0
	limit=100
	while(1):
		vmlist=vm_api_instance.list_vms(_limit=limit, _page=page)
		for vm in vmlist.data:
			my_vms.append(vm)
		if len(vmlist.data) < limit:
			print(f"Less than {limit} VMs retrieved, stopping.  Retrieved {len(vmlist.data)} VMs on this page")
			break
		page+=1
		count+=1
		print(f"Retrieved {len(vmlist.data)} VMs from page {page-1}")
	print(f"Retrieved {len(my_vms)} VMs from the cluster")
	return my_vms
```
###### Call the function
Similar to the REST version above but using object dot `.` notation rather than dict `['name']` format.
```
vms=get_vm_list_sdk()
for vm in vms:
	extId=vm.ext_id
	name=vm.name
	print(f"VM Name: {name} - Ext ID: {extId}")
```
##### Screenshots

###### Postman
---
![Postman API](https://github.com/garyjlittle/n0derunner/blob/b59811fb79d2a07be52118a6fe2e3faa1d5d55d0/screenshots/postman-v4-api.png)
---
###### vscode
---
![VSCode Explorer](https://github.com/garyjlittle/n0derunner/blob/b59811fb79d2a07be52118a6fe2e3faa1d5d55d0/screenshots/v4-api-vscode-explore.png)
---
