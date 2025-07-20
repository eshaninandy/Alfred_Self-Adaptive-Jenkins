import requests, jenkins, datetime, time, pandas as pd, threading, os, subprocess, sys, fnmatch, platform, yaml, re
from sdcclient import SdMonitorClient
from sdcclient import IbmAuthHelper
from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference, Series
import numpy as np
# Jenkins server details
jenkins_url = 'http://jenkins-service-devops-tools.mycluster-ca-tor-2-bx2-4x-04e8c71ff333c8969bc4cbc5a77a70f6-0000.ca-tor.containers.appdomain.cloud/'

username = 'g2campos' # Replace with your credentials
password = '12345678' # Replace with your credentials
server = jenkins.Jenkins(jenkins_url, username, password)  # Connect to Jenkins


# IBM Cloud details
GUID = '3fed93bc-00f4-4651-8ce2-e73ba4b9a918'
APIKEY = 'romxT2UokCNovPFym7zlpdhMqV6xPEEiLiBGbl7pGrfW'
URL = 'https://ca-tor.monitoring.cloud.ibm.com'

# Initialize client
ibm_headers = IbmAuthHelper.get_headers(URL, APIKEY, GUID)
sdclient = SdMonitorClient(sdc_url=URL, custom_headers=ibm_headers)

# Metrics list to export (CPU, Memory, and Network Error Count)
metrics_to_collect = [
    {"id": "container.name"},
    {"id": "cpu.cores.used", "aggregations": {"time": "timeAvg", "group": "avg"}},
    {"id": "cpu.cores.quota.limit", "aggregations": {"time": "timeAvg", "group": "avg"}},
    {"id": "memory.bytes.used", "aggregations": {"time": "timeAvg", "group": "avg"}},
    {"id": "memory.limit.bytes", "aggregations": {"time": "timeAvg", "group": "avg"}}
]

# Data filter and time window
filter = "kube_namespace_name='devops-tools'"
start = -1200
end = 0
sampling = 10

################# MONITOR PHASE #####################
# Monitoring Jenkins Time metrics
def get_builds_info(job_name):
    # In this part here I'm collecting the information of the last 30 builds
    job_info = server.get_job_info(job_name)
    list_of_builds = job_info['builds'][:50]
       
    builds_info_list = []

    # from the 30 last builds we will iterate over each one and..
    for build in list_of_builds:
        # This command gets everything that we want essentially: Who ran the build, blockedDurationMillis, etc.
        build_info = server.get_build_info(job_name, build['number'])
        
        # Basic details
        build_details = {
            'Job Name': job_name,
            'Build Number': build_info['number'],
            'Status': build_info['result'],
            'Total Duration (s)': round(build_info['duration'] / 1000, 2),
            'Time in Queue (s)': 0,  # Default value for buildableTimeMillis
            'Blocked Time (s)': 0,  # Default value for blockedTimeMillis
            'Waiting Time (s)': 0,  # Default value for waitingTimeMillis
            'Build Time (s)': 0  # Placeholder for Building Duration - Time in Queue
        }

        # Extract relevant time metrics from actions
        for action in build_info.get('actions', []):
            if isinstance(action, dict):
                if 'buildableTimeMillis' in action:
                    build_details['Time in Queue (s)'] = round(action['buildableTimeMillis'] / 1000, 2)
                if 'blockedTimeMillis' in action:
                    build_details['Blocked Time (s)'] = round(action['blockedTimeMillis'] / 1000, 2)
                if 'waitingTimeMillis' in action:
                    build_details['Waiting Time (s)'] = round(action['waitingTimeMillis'] / 1000, 2)

        # Calculate "Total Duration (s) - Time in Queue"
        build_details['Build Time (s)'] = max(
            build_details['Total Duration (s)'] - build_details['Time in Queue (s)'], 0
        )

        # Append the processed build details
        builds_info_list.append(build_details)

    return builds_info_list

# Monitoring Jenkins Container metrics
def collect_container_data():
    # Load data with start, end, and sampling values
    ok, res = sdclient.get_data(metrics_to_collect, start, end, sampling, filter=filter, datasource_type='container')

    container_data = []
    
    if ok:
        data = res['data']
        
        # Extract container names and CPU usage from the data
        for d in data:
            container_name = d['d'][0]  # Assuming container name is the first field
            container_cpu = d['d'][1]  # Assuming CPU usage is the second field
            container_cpu_limit = d['d'][2] # Assuming CPU limit is the third field
            container_memory = d['d'][3] # Assuming Memory limit is the fifth field
            container_memory_limit = d['d'][4] # Assuming Memory usage is the fourth field

            # Create a dictionary for each container with name and CPU usage
            container_details = {
                'Container Name': container_name,
                'Container CPU Usage': container_cpu,
                'Container CPU Limit': container_cpu_limit,
                'Container Memory Usage': container_memory,
                'Container Memory Limit': container_memory_limit
            }
            container_data.append(container_details)
        
        return container_data
    else:
        print("Failed to retrieve data")
        return []

# Exporting Jenkins Time metrics
#This method will save the data collected in an excel and will also return the data collected to further use in the code
def export_jenkins_time_metrics_to_excel():
    # Export Monitored Jenkins Time Metrics
    time_combined_info = []
    for job in server.get_all_jobs():
        builds_info = get_builds_info(job['name'])
        time_combined_info.extend(builds_info)
    
    df = pd.DataFrame(time_combined_info)
    output_file = 'builds_info.xlsx'
    df.to_excel(output_file, index=False)
    print(f"Build information written to {output_file}")
    
    return time_combined_info

# Exporting Jenkins Container metrics
#This method will save the data collected in an excel and will also return the data collected to further use in the code
def export_jenkins_container_metrics_to_excel():
    # Export Monitored Jenkins Container Metrics
    container_combined_info = []
    for job in server.get_all_jobs():
        container_data = collect_container_data()
        container_combined_info.extend(container_data)
    
    df = pd.DataFrame(container_combined_info)
    output_file = 'container_data.xlsx'
    df.to_excel(output_file, index=False)
    print(f"Build information written to {output_file}")
    
    return container_combined_info

################# ANALYSIS PHASE #####################
def Memory_Average(container_metrics):
    sum_of_entries = 0
    count = 0
    for container in container_metrics:
        if 'Container Memory Usage' in container:  # Check if the key exists in the dictionary
            sum_of_entries += float(container['Container Memory Usage'])
            count += 1
    if count > 0:
        average_memory_usage = sum_of_entries / count
        return average_memory_usage
    else:
        return None
       
#this method is currently only "printing" but it should evolve to returning something       
def Memory_Threshold_Check(define_threshold, calculated_average):
    if calculated_average >= define_threshold:
        return True
    else:
        return False

################# PLANNING PHASE #####################
def build_time_calculator(builds_data):
    """
    Extracts the last 10 builds' times after subtracting the waiting time.

    Args:
    - builds_data (list): List of build dictionaries containing 'Total Duration (s)' and 'Waiting Time (s)'.

    Returns:
    - list: Array of adjusted times (Building Duration - Waiting Time).
    """
    # Sort builds by Build Number in descending order to ensure the last 10 are the most recent
    sorted_builds = sorted(builds_data, key=lambda x: x['Build Number'], reverse=True)
    
    # Extract the last 10 builds
    last_10_builds = sorted_builds[:10]
    
    # Calculate adjusted times (Building Duration - Waiting Time)
    building_time = [
        build['Total Duration (s)'] - build['Time in Queue (s)'] for build in last_10_builds
    ]
    
    return building_time

def queue_time_calculator(builds_data):
    """
    Extracts the last 10 builds' times after subtracting the waiting time.

    Args:
    - builds_data (list): List of build dictionaries containing 'Total Duration (s)' and 'Waiting Time (s)'.

    Returns:
    - list: Array of adjusted times (Building Duration - Waiting Time).
    """
    # Sort builds by Build Number in descending order to ensure the last 10 are the most recent
    sorted_builds = sorted(builds_data, key=lambda x: x['Build Number'], reverse=True)
    
    # Extract the last 10 builds
    last_10_builds = sorted_builds[:30]
    
    # Calculate adjusted times (Building Duration - Waiting Time)
    queue_times = [
        build['Time in Queue (s)'] for build in last_10_builds
    ]
    
    return queue_times

def build_time_average_calculator(values, z_threshold=2):
    """
    Process data to eliminate outliers, calculate average, and add deviation.

    Args:
    - values (list or array): Input array of numerical values.
    - z_threshold (float): Z-score threshold to identify outliers (default=3).

    Returns:
    - dict: Contains original average, filtered average, and final result.
    """
    # Convert input to a numpy array
    values = np.array(values)

    # Calculate mean and standard deviation
    mean = np.mean(values)
    std_dev = np.std(values)

    # Calculate z-scores
    z_scores = (values - mean) / std_dev

    # Filter out outliers
    filtered_values = values[np.abs(z_scores) <= z_threshold]

    # Calculate average of filtered values
    filtered_average = np.mean(filtered_values)

    # Add deviation to the average
    final_result = filtered_average + np.std(filtered_values)

    # Return results
    return {
        "original_average": mean,
        "filtered_average": filtered_average,
        "final_result": final_result,
        "filtered_values": filtered_values.tolist(),
    }

################# PLANNING PHASE #####################
def memory_monitoring(threshold, interval):
    """
    Continuously monitor memory usage and break if the threshold is exceeded.

    Args:
        threshold (float): Memory usage threshold in MB.
        interval (int): Time interval in seconds for checking memory usage.
    """
    try:
        print(f"Starting memory monitoring. Threshold: {threshold} B...")
        while True:
            container_metrics = collect_container_data()
            average_memory_usage = Memory_Average(container_metrics)
            
            if average_memory_usage is None:
                print("No memory usage data available. Retrying...")
                time.sleep(interval)
                continue
            
            if Memory_Threshold_Check(threshold, average_memory_usage):
                scale_in_executors('node-1')
                jobs_to_be_retriggered = cancel_jobs_being_built()
                break
            
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user.")
    except Exception as e:
        print(f"An error occurred: {e}")

################# EXECUTE PHASE #####################

def disable_jenkins_job(job_name_to_disable):
    job_info = server.disable_job(job_name_to_disable)

def enable_jenkins_job(job_name_to_enable):
    job_info = server.enable_job(job_name_to_enable)

def scale_out_executors(node_name):
    try:
        # Step 1: Get the current node configuration
        current_config = server.get_node_config(node_name)
    
        # Step 2: Extract the current value of <numExecutors> using regex
        match = re.search(r"<numExecutors>(\d+)</numExecutors>", current_config)
        if match:
            current_executor_count = int(match.group(1))  # Extract the current value as an integer
            new_executor_count = current_executor_count + 1  # Increment the value by 1
    
            # Step 3: Replace the <numExecutors> value in the XML
            updated_config = re.sub(
                r"<numExecutors>\d+</numExecutors>",
                f"<numExecutors>{new_executor_count}</numExecutors>",
                current_config
            )
    
            # Debug: Print the updated configuration
            print("Updated Configuration:")
            print(updated_config)
    
            # Step 4: Push the updated configuration back to Jenkins
            server.reconfig_node(node_name, updated_config)
            print(f"Successfully updated the configuration for node '{node_name}'.")
        else:
            print("Error: Could not find the <numExecutors> element in the configuration XML.")
    except jenkins.JenkinsException as e:
        print(f"Failed to update node configuration: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def scale_in_executors(node_name):
    try:
        # Step 1: Get the current node configuration
        current_config = server.get_node_config(node_name)
    
        # Step 2: Extract the current value of <numExecutors> using regex
        match = re.search(r"<numExecutors>(\d+)</numExecutors>", current_config)
        if match:
            current_executor_count = int(match.group(1))  # Extract the current value as an integer
            new_executor_count = current_executor_count - 1  # Increment the value by 1
    
            # Step 3: Replace the <numExecutors> value in the XML
            updated_config = re.sub(
                r"<numExecutors>\d+</numExecutors>",
                f"<numExecutors>{new_executor_count}</numExecutors>",
                current_config
            )
    
            # Debug: Print the updated configuration
            print("Updated Configuration:")
            print(updated_config)
    
            # Step 4: Push the updated configuration back to Jenkins
            server.reconfig_node(node_name, updated_config)
            print(f"Successfully updated the configuration for node '{node_name}'.")
        else:
            print("Error: Could not find the <numExecutors> element in the configuration XML.")
    except jenkins.JenkinsException as e:
        print(f"Failed to update node configuration: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def cancel_jobs_being_built():
    """
    Cancels all jobs that are currently being built.
    """
    try:
        # Retrieve the list of running builds
        jobs_being_built = server.get_running_builds()

        # Check if there are any running jobs
        if not jobs_being_built:
            print("No jobs are currently being built.")
            return

        print(f"Found {len(jobs_being_built)} jobs being built. Cancelling them now...")

        # Iterate through each running job and cancel it
        for job in jobs_being_built:
            job_name = job['name']
            build_number = job['number']

            print(f"Cancelling job: {job_name}, Build Number: {build_number}...")

            try:
                # Stop the build using Jenkins API
                server.stop_build(job_name, build_number)
                print(f"Successfully cancelled job: {job_name}, Build Number: {build_number}.")
            except Exception as e:
                print(f"Failed to cancel job: {job_name}, Build Number: {build_number}. Error: {str(e)}")
        return jobs_being_built
    except Exception as e:
        print(f"An error occurred while fetching running builds: {str(e)}")

    
################# RUNTIME PHASE #####################

#Possible solutions:
# Disable or Enable Job
# Scale up or down the Container size

#These two lines here are running the export of the data as well as collecting its results and saving them to local variables

def get_all_jobs():
    """
    Get all jobs from the Jenkins server.
    """
    try:
        jobs = server.get_all_jobs()
        job_names = [job['name'] for job in jobs]
        print(f"Found {len(job_names)} jobs:")
        for job in job_names:
            print(f"- {job}")
        return job_names
    except Exception as e:
        print(f"Failed to retrieve jobs. Error: {str(e)}")
        return []

if __name__ == "__main__":
    export_jenkins_time_metrics_to_excel()
    export_jenkins_container_metrics_to_excel()
    job_names = get_all_jobs()
    for job_name in job_names:
        job_data = get_builds_info(job_name)
        
        # Get adjusted times
        building_time = build_time_calculator(job_data)
        queue_time = queue_time_calculator(job_data)
        
        
        # Output the results
        print("Adjusted Times (Last 10 Builds):", building_time)
        
        # Example usage
        values = building_time  # Example data
        results = build_time_average_calculator(values)
        
        print("Original Average:", results["original_average"])
        print("Filtered Average:", results["filtered_average"])
        print("Final Result (Avg + Deviation):", results["final_result"])
        print("Filtered Values (No Outliers):", results["filtered_values"])
        print()

