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
start = -30
end = 0
sampling = 10

################# MONITOR PHASE #####################
# Monitoring Jenkins Time metrics
def get_builds_info(job_name):
    # In this part here I'm collecting the information of the last 30 builds
    job_info = server.get_job_info(job_name)
    list_of_builds = job_info['builds'][:30]
       
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
    last_10_builds = sorted_builds[:10]
    
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
def monitor_queue_and_adjust_executors(retriggered_jobs, node_name):
    """
    Monitor Jenkins queue and reduce executors when retriggered jobs are next in line.
    
    Args:
    - retriggered_jobs (list): List of retriggered job names.
    - node_name (str): The Jenkins node to adjust executors for.
    """
    try:
        print("Monitoring Jenkins queue for retriggered jobs...")
        while True:
            queue = server.get_queue_info()
            
            if not queue:
                print("The Jenkins queue is empty. Stopping monitoring.")
            
            # Check if retriggered jobs are next in line
            for item in queue:
                job_name = item.get('task', {}).get('name', '')
                if job_name in retriggered_jobs:
                    print(f"Job {job_name} is next in the queue. Reducing executors on {node_name}.")
                    scale_in_executors(node_name)
                    retriggered_jobs.remove(job_name)  # Remove the job from the list after handling
                    return  # Exit monitoring once action is taken
            
            print("Retriggered jobs are not next in the queue. Waiting before rechecking...")
            time.sleep(5)  # Adjust the polling interval as needed
    except Exception as e:
        print(f"An error occurred while monitoring the queue: {str(e)}")


def memory_monitoring_with_queue(threshold, interval, node_name):
    """
    Continuously monitor memory usage and handle high memory situations.

    Args:
        threshold (float): Memory usage threshold in bytes.
        interval (int): Time interval in seconds for checking memory usage.
        node_name (str): The Jenkins node to adjust executors for.
    """
    retriggered_jobs = []  # Initialize retriggered_jobs as an empty list
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
                print("Memory threshold exceeded. Cancelling the most recently triggered job.")
                last_retriggered_job = cancel_last_triggered_job()
                if last_retriggered_job:
                    retriggered_jobs.append(last_retriggered_job)
                    # Start monitoring retriggered jobs in a separate thread
                    threading.Thread(
                        target=monitor_queue_and_adjust_executors, 
                        args=(retriggered_jobs, node_name)
                    ).start()

            # Continue monitoring after actions
            print(f"Memory usage is under control: {average_memory_usage} B")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user.")
    except Exception as e:
        print(f"An error occurred: {e}")


def monitor_queue_and_scale_executors(max_queue_size, queue_time_threshold, max_executors, node_name):
    """
    Monitor Jenkins queue and increase executors based on the queue size and job wait time.

    Args:
    - max_queue_size (int): Maximum queue size before scaling out executors.
    - queue_time_threshold (int): Maximum time in seconds a job can spend in the queue before scaling out executors.
    - max_executors (int): Maximum allowed executor nodes for scaling out.
    - node_name (str): Jenkins node to adjust executors for.
    """
    try:
        print("Monitoring Jenkins queue to scale executors...")
        while True:
            # Get the queue info
            queue = server.get_queue_info()

            # Check if the queue is empty
            if not queue:
                print("The Jenkins queue is empty. No scaling needed.")
                time.sleep(5)
                continue

            # Check the queue size
            if len(queue) > max_queue_size:
                print(f"Queue size {len(queue)} exceeds the maximum allowed {max_queue_size}. Scaling out executors.")
                scale_out_executors_if_possible(node_name, max_executors)
                time.sleep(5)
                continue

            # Check job wait times
            for item in queue:
                in_queue_since = item.get('inQueueSince', None)
                task_name = item.get('task', {}).get('name', 'Unknown')

                if in_queue_since is None:
                    print(f"Skipping item due to missing 'inQueueSince': {item}")
                    continue

                job_wait_time = (time.time() * 1000 - in_queue_since) / 1000  # Convert from ms to seconds
                if job_wait_time > queue_time_threshold:
                    print(f"Job {task_name} has been in the queue for {job_wait_time:.2f} seconds. Scaling out executors.")
                    scale_out_executors_if_possible(node_name, max_executors)
                    break

            print("Queue is within acceptable limits. No scaling needed.")
            time.sleep(5)  # Adjust the polling interval as needed
    except Exception as e:
        print(f"An error occurred while monitoring the queue: {str(e)}")



def scale_out_executors_if_possible(node_name, max_executors):
    """
    Increase the number of executors if the current count is below the maximum limit.

    Args:
    - node_name (str): Jenkins node to adjust executors for.
    - max_executors (int): Maximum allowed executors.
    """
    try:
        # Get the current node configuration
        current_config = server.get_node_config(node_name)

        # Extract the current number of executors
        match = re.search(r"<numExecutors>(\d+)</numExecutors>", current_config)
        if match:
            current_executor_count = int(match.group(1))
            if current_executor_count < max_executors:
                # Increase executors by 1
                new_executor_count = current_executor_count + 1
                updated_config = re.sub(
                    r"<numExecutors>\d+</numExecutors>",
                    f"<numExecutors>{new_executor_count}</numExecutors>",
                    current_config
                )
                server.reconfig_node(node_name, updated_config)
                print(f"Scaled out executors to {new_executor_count} on node '{node_name}'.")
            else:
                print(f"Executor count {current_executor_count} has reached the maximum allowed {max_executors}.")
        else:
            print("Error: Could not find the <numExecutors> element in the configuration XML.")
    except Exception as e:
        print(f"Failed to scale out executors: {e}")

################# EXECUTE PHASE #####################

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

def cancel_last_triggered_job():
    """
    Cancels the most recently triggered job, deletes the build, and retriggers it.
    """
    try:
        # Retrieve the list of running builds
        jobs_being_built = server.get_running_builds()

        # Check if there are any running jobs
        if not jobs_being_built:
            print("No jobs are currently being built.")
            return None  # Return None if no jobs are being built

        # Find the most recently triggered job based on the build number
        last_triggered_job = max(jobs_being_built, key=lambda job: job['number'])

        job_name = last_triggered_job['name']
        build_number = last_triggered_job['number']
        print(f"Cancelling the most recently triggered job: {job_name}, Build Number: {build_number}...")

        # Stop the build
        try:
            server.stop_build(job_name, build_number)
            print(f"Successfully cancelled job: {job_name}, Build Number: {build_number}.")
        except Exception as e:
            print(f"Failed to cancel job: {job_name}, Build Number: {build_number}. Error: {str(e)}")
            return None

        # Delete the build
        try:
            print(f"Deleting canceled job build: {job_name}, Build Number: {build_number}...")
            server.delete_build(job_name, build_number)
            print(f"Successfully deleted build: {job_name}, Build Number: {build_number}.")
        except Exception as e:
            print(f"Failed to delete build: {job_name}, Build Number: {build_number}. Error: {str(e)}")
            return None

        # Retrigger the job
        try:
            print(f"Retriggering job: {job_name}")
            server.build_job(job_name)
            print(f"Successfully retriggered job: {job_name}")
            return job_name  # Return the job name that was retriggered
        except Exception as e:
            print(f"Failed to retrigger job: {job_name}. Error: {str(e)}")
            return None

    except Exception as e:
        print(f"An error occurred while canceling and retriggering the job: {str(e)}")
        return None
    
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
    memory_threshold = 6.5 * (10**9)  # Define your threshold in bytes
    monitoring_interval = 2  # Check every 2 seconds
    node_name = 'node-1'  # Node to adjust executors for
    max_queue_size = 8  # Maximum acceptable queue size
    queue_time_threshold_1 = 300  # Maximum queue time in seconds

    max_executors = 4  # Maximum number of executors allowed

    # Start memory monitoring and queue scaling in parallel
    memory_monitor_thread = threading.Thread(
        target=memory_monitoring_with_queue, args=(memory_threshold, monitoring_interval, node_name)
    )
    queue_monitor_thread = threading.Thread(
        target=monitor_queue_and_scale_executors, args=(max_queue_size, queue_time_threshold_1, max_executors, node_name)
    )

    memory_monitor_thread.start()
    queue_monitor_thread.start()

    memory_monitor_thread.join()
    queue_monitor_thread.join()
