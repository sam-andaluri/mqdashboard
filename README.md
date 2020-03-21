# MQ Dashboard

This Serverless project helps customers simplify their operations by generating automated CloudWatch dashboards 
for AmazonMQ. The Amazon Lambda generates dashboards on a specified interval.

## Features

  - Generates predefined dashboards containing specific metrics that would be useful to monitor brokers and associated queues and topics.
  
  - The root or main dashboard named AmazonMQ contains all brokers in a given region. Supports both single instance and Active/Standby brokers. 
  
  - For each broker, the app automatically enumerates all queues and topics. 
  
  - For each queue/topic, the dashboard generated shows the useful metrics.
  
  - All dashboards are generated every 30 minutes, capturing any new brokers, queues or topics created in the past 30 minutes.
  
  - This repository includes all code necessary. 
  
  - Generates CPU, HeapUsage and StorePercentage alarms for all brokers.
  
  - Generates No consumer alerts for queues and topics.

## Deployment

  - If you are deploying from Serveless Application Repository, just deploy directly.
  
  - If you are cloning the repo from github, use the following commands:
  ```shell script
sam build --template mqdashboard.yaml
sam package --template-file mqdashboard.yaml --output-template-file packaged.yaml --s3-bucket <s3 bucket>
sam deploy --template-file packaged.yaml --stack-name <YOUR STACK NAME>
```   

## Usage Notes

  - After deploying the application in a given region, the root dashboard is named **AmazonMQ-<region>**
  
  - Once you click on the root dashboard, it shows all brokers in that region.
  
  - For each broker, if you click on the link takes you to another dashboard that lists queues and topics and shows useful charts for the broker.
  
  - For each queue/topic, if you click on the link shows useful charts for that object.

