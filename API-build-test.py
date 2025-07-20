import jenkins
import random
import time

# Jenkins server details
jenkins_url = 'http://jenkins-service-devops-tools.mycluster-ca-tor-2-bx2-4x-04e8c71ff333c8969bc4cbc5a77a70f6-0000.ca-tor.containers.appdomain.cloud/'
username = 'g2campos'  # Replace with your credentials
password = '12345678'  # Replace with your credentials

# Connect to Jenkins
server = jenkins.Jenkins(jenkins_url, username, password)


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


def get_jenkins_queue():
    """
    Get the current queue from Jenkins.
    """
    try:
        queue = server.get_queue_info()
        if queue:
            print(f"There are {len(queue)} jobs in the queue.")
        else:
            print("The Jenkins queue is empty.")
        return queue
    except Exception as e:
        print(f"Failed to retrieve the queue. Error: {str(e)}")
        return []


def get_running_builds():
    """
    Get a list of currently running builds.
    """
    try:
        running_builds = server.get_running_builds()
        if running_builds:
            print(f"There are {len(running_builds)} running builds.")
        else:
            print("No builds are currently running.")
        return running_builds
    except Exception as e:
        print(f"Failed to retrieve running builds. Error: {str(e)}")
        return []


def trigger_builds_randomly(job_names):
    """
    Trigger all jobs in a random order.
    """
    random.shuffle(job_names)  # Shuffle the list to randomize order
    print("Triggering jobs in the following random order:")
    for job_name in job_names:
        print(f"- {job_name}")
    for job_name in job_names:
        try:
            server.build_job(job_name)
            print(f"Triggered build for job: {job_name}")
            time.sleep(1)  # Add a slight delay between triggers
        except Exception as e:
            print(f"Failed to trigger a build for job: {job_name}. Error: {str(e)}")


def monitor_and_trigger_jobs(interval=15):
    """
    Monitor Jenkins queue and builds. When idle, trigger all jobs randomly.

    Args:
    - interval (int): Time in seconds to wait between each status check.
    """
    job_names = get_all_jobs()
    if not job_names:
        print("No jobs available to trigger. Exiting.")
        return

    while True:
        print("\nChecking Jenkins queue and running builds...")
        queue = get_jenkins_queue()
        running_builds = get_running_builds()

        if not queue and not running_builds:
            print("Queue is empty, and no builds are running. Triggering all jobs randomly.")
            trigger_builds_randomly(job_names)
        else:
            print("Jobs are still in progress. Waiting before rechecking.")

        print(f"Waiting for {interval} seconds before checking again...\n")
        time.sleep(interval)


if __name__ == "__main__":
    monitor_and_trigger_jobs(interval=15)
