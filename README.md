# MQ Dashboard

This project helps customers simplify their AmazonMQ operations by generating automated CloudWatch dashboards 
for AmazonMQ. Amazon Lambda is used to generate the dashboards on a specified interval. 

## Features

  - Generates predefined dashboards containing specific metrics that would be useful to monitor brokers and their associated queues and topics.
  
  - The root or main dashboard named AmazonMQ contains all brokers in a given region. Supports both single instance and Active/Standby brokers. 
  
  - For each broker, the code automatically enumerates all queues and topics. 
  
  - For each queue/topic, the dashboard generated shows the useful metrics.
  
  - All dahsboards are generated every 12 hours, capturing any new brokers, queues or topics created in the past 12 hours.
  
  - This repository includes all code necessary. Customers can tweak the code/intervals as necessary.
  
>Please feel free to fork this project, submit issues or pull requests.


