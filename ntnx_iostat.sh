#!/usr/bin/env bash

#
# A simple bash script to print out read and write IOP
# figures for a single container in a nutanix cluster.
#

# IP here is the cluster VIP
VIP=""
# Prism username
username=""
# Prism password
password=""
# Container to measure
container_list=""

function main {
    let count=0
    while true  ; do
        for container in $container_list ; do
            CTR_UUID=$(get_uuid_for_container $container)
            if [[ $(($count % 10)) -eq 0 ]] ; then
                    DATE=$(date)
                    printf "%s\t%s\tContainer=%s\n" "READ IOPS" "WRITE IOPS" $container
            fi
            READ_IOPS=$(get_metric $CTR_UUID "controller_num_read_iops")
            WRITE_IOPS=$(get_metric $CTR_UUID "controller_num_write_iops")
            printf "%9d\t%10d\n" $READ_IOPS $WRITE_IOPS
            let count=$count+1
            done
        sleep 10
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
