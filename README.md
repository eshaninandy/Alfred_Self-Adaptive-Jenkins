# ALFRED: A Self-Adaptive Jenkins

**Authors**: 
- Eshani Nandy ([enandy@uwaterloo.ca](mailto:enandy@uwaterloo.ca))
- Guilherme Campos ([g2campos@uwaterloo.ca](mailto:g2campos@uwaterloo.ca))

**Course Project — ECE750, University of Waterloo**

---

## Overview

ALFRED is a self-adaptive extension for Jenkins that automates the management of build queues and executor resources. By integrating a custom MAPE-K (Monitor, Analyze, Plan, Execute, Knowledge) loop, ALFRED dynamically adjusts Jenkins' configuration in response to fluctuating workloads—without manual intervention.

---

## Motivation

Jenkins, a widely used CI/CD automation server, often suffers from build queue congestion and inefficient resource use in high-commit environments. Existing solutions rely on static plugins or manual tuning. ALFRED addresses these challenges by:

- Reducing job wait time in queue
- Dynamically scaling the number of executors
- Managing memory usage to prevent Jenkins crashes
- Automating decision-making via self-adaptive logic

---

## Key Features

- MAPE-K loop for runtime feedback control
- Real-time monitoring of Jenkins metrics via Python-Jenkins API and IBM Cloud Monitoring
- Dynamic scaling of executors based on queue congestion and resource thresholds
- Intelligent job cancellation and re-triggering to maintain system stability
- Tested on diverse workloads using 12 GitHub repositories

---

## Architecture and Tools

- Jenkins(Dockerized): CI/CD platform orchestrating builds
- Python-Jenkins API: Automates Jenkins monitoring and control
- IBM Cloud: Hosts and monitors the Jenkins container
- Docker: Provides isolated and reproducible environment
- MAPE-K Framework**: Implements self-adaptive behavior

---

## Experiments and Results

**Setup:**  
- 120 builds across 12 GitHub repositories  
- Initial agent node with 1 executor  
- Metrics collected: queue length, wait time, memory and CPU usage

**Without adaptation:**  
- Manual scaling to 2, 3, and 4 executors showed reduced queue time but led to memory overuse and Jenkins crashes

**With adaptation:**  
- Queue wait times reduced significantly
- Memory usage remained within safe thresholds
- Executor scaling and job cancellation handled automatically

**Result Summary:**

| Configuration     | Queue Time | Memory Usage | Manual Intervention |
|------------------|------------|---------------|---------------------|
| Without ALFRED   | High       | Unstable      | Required            |
| With ALFRED      | Low        | Stable        | None                |

---

## Repository Structure

- [`driver.py`](https://git.uwaterloo.ca/g2campos/ece750-t37-driver-codes): MAPE-K loop implementation
- [`Dockerfile`](https://git.uwaterloo.ca/g2campos/ece750-t37-driver-codes): Jenkins setup with Python support
- [`metrics.xlsx`](https://git.uwaterloo.ca/g2campos/ece750-t37-driver-codes): Recorded experimental data
- [`jenkins-jobs`](https://git.uwaterloo.ca/g2campos/ece750-t37-jenkins-jobs): Sample GitHub CI/CD pipelines

---

## Metrics Tracked

- Queue length
- Wait time in queue
- Number of executors
- Memory bytes used and limit
- CPU cores used and limit

---

## Setup and Usage

1. Clone the repository:

   ```bash
   git clone https://git.uwaterloo.ca/g2campos/ece750-t37-driver-codes
   cd ece750-t37-driver-codes
   ```
2. Build the Jenkins Docker image:
```bash
docker build -t custom-jenkins .
```
3. Deploy the Docker container on IBM Cloud or any compatible environment with memory and CPU limits configured.

4. Start Jenkins and assign one executor to the agent node through Jenkins UI or configuration files.

5. Run the adaptation script to enable the MAPE-K loop:
```bash
python3 driver.py
```

---
## Future Work
Add machine learning for threshold prediction

Extend to support multi-node Jenkins deployments

Improve support for interdependent job pipelines

---
## License
Reuse permitted with citation.

---
## Related Links
[MAPE-K Overview](https://en.wikipedia.org/wiki/MAPE-K)

[Jenkins Documentation](https://www.jenkins.io/doc/)

[IBM Cloud Docs](https://cloud.ibm.com/docs)
