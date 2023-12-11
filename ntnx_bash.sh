#!/usr/bin/env bash

# IP here is the cluster VIP
VIP=""
username=""
password=""
container_list=""

function main {
	printf "Content-Type: text/plain\n\n"
        for container in $container_list ; do
            CTR_UUID=$(get_uuid_for_container $container)
            READ_IOPS=$(get_metric $CTR_UUID "controller_num_read_iops")
            WRITE_IOPS=$(get_metric $CTR_UUID "controller_num_write_iops")
            echo "ntnx_bash{metric=\"cluster_read_iops\"} $READ_IOPS" 
            echo "ntnx_bash{metric=\"cluster_write_iops\"} $WRITE_IOPS" 
        done
}

function get_metric {
    CTR_UUID=$1
    metric_name=$2
    URL="https://$VIP:9440/PrismGateway/services/rest/v2.0/storage_containers/$CTR_UUID/stats/?metrics=$metric_name" 
    JSON=$(curl -S -u "$username:$password" -k -X GET --header 'Accept: application/json' $URL 2>/dev/null)
    RES=$(echo $JSON | jq '.["stats_specific_responses"][0]["values"][0]')
    echo "$RES"
}

function get_uuid_for_container {
    CTR_NAME=$1
    URL="https://$VIP:9440/PrismGateway/services/rest/v2.0/storage_containers/?search_string=$CTR_NAME"
    JSON=$(curl -S -u "$username:$password" -k -X GET --header 'Accept: application/json' $URL 2>/dev/null)
    RES=$(echo $JSON | jq '.["entities"][0]["storage_container_uuid"]'| sed s/\"//g)
    echo $RES
}
# Call main function.
main
