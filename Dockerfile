# Use the official Jenkins LTS image as the base image
FROM jenkins/jenkins:lts

# Switch to root to install packages
USER root

# Update package lists and install Python, pip, python3-venv, and Java
RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-venv openjdk-17-jdk && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create a symbolic link to use `python` as a command (optional)
RUN ln -s /usr/bin/python3 /usr/local/bin/python

# Switch back to the Jenkins user
USER jenkins
