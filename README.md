# MQ Dashboard

This Serverless project helps customers simplify their AmazonMQ operations by generating automated CloudWatch dashboards 
for AmazonMQ. The Amazon Lambda generates dashboards on a specified interval.

## Features

  - Generates predefined dashboards containing specific metrics that would be useful to monitor brokers and associated queues and topics.
  
  - The root or main dashboard named AmazonMQ contains all brokers in a given region. Supports both single instance and Active/Standby brokers. 
  
  - For each broker, the app automatically enumerates all queues and topics. 
  
  - For each queue/topic, the dashboard generated shows the useful metrics.
  
  - All dashboards are generated every 12 hours, capturing any new brokers, queues or topics created in the past 12 hours.
  
  - This repository includes all code necessary. 

## Deployment

  - If you are deploying from Serveless Application Repository, just deploy directly.
  
  - If you are cloning the repo from github, use the following commands:
  ```shell script
sam build --template mqdashboard.yaml
sam package --template-file mqdashboard.yaml --output-template-file packaged.yaml --s3-bucket <s3 bucket>
sam deploy --template-file packaged.yaml --stack-name <YOUR STACK NAME>
```   

