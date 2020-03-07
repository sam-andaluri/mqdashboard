import copy
import json
import boto3

# AWS API clients
mq = boto3.client('mq')
cw = boto3.client('cloudwatch')

# Dashboard names can only have a dash or underscore.
def getObjectDashboardName(objectName):
    return objectName.replace(".", "-")

# Generate a CW dashboard URL markdown for a given queue
def generateObjectURLMd(objectName, displayName, brokerRegion):
    return """[""" + displayName + """](https://console.aws.amazon.com/cloudwatch/home?region=""" + brokerRegion + """#dashboards:name=""" + getObjectDashboardName(
        objectName) + """)\n\n"""

# Given a broker, enumerate queues and topics for that broker
def getListOfQueuesAndTopics(brokerName, queueList, topicList):
    # Get a list of metrics for AmazonMQ and a broker. This would help enumerate queues and topics
    resp = cw.list_metrics(Namespace="AWS/AmazonMQ", Dimensions=[{'Name': 'Broker', 'Value': brokerName}])
    for metrics in resp['Metrics']:
        for dimensions in metrics['Dimensions']:
            if dimensions['Name'] == 'Queue':
                queueList.add(dimensions['Value'])
            if dimensions['Name'] == 'Topic':
                topicList.add(dimensions['Value'])

# Generates a CW dashboard for each broker including a list of queues and topics
def generateObjectDashboard(brokerName, brokerRegion):
    # Init queueList set.
    queueList = set()
    topicList = set()

    # MQ client does not have API for listing queues and topics.
    # Use the CW client to get the queue and topic list.
    getListOfQueuesAndTopics(brokerName, queueList, topicList)

    # Read the queue dashboard template to generate a new dashboard for each queue
    queueTemplateJson = json.loads(queue_dashboard_template, strict=False)
    for queueName in queueList:
        queueJson = copy.copy(queueTemplateJson)
        queueJson['widgets'][0]['properties']['markdown'] = """\n ## Queue metrics for **""" + queueName + """**\n"""
        for widget in queueJson['widgets']:
            if widget['type'] == 'metric':
                widget['properties']['metrics'][0][3] = brokerName
                widget['properties']['metrics'][0][5] = queueName
                widget['properties']['region'] = brokerRegion
        cw.put_dashboard(DashboardName=getObjectDashboardName(queueName), DashboardBody=json.dumps(queueJson))

    # Read the topic dashboard template to generate a new dashboard for each topic
    topicTemplateJson = json.loads(topic_dashboard_template, strict=False)
    for topicName in topicList:
        topicJson = copy.copy(topicTemplateJson)
        topicJson['widgets'][0]['properties']['markdown'] = """\n ## Topic metrics for **""" + topicName + """**\n"""
        for widget in topicJson['widgets']:
            if widget['type'] == 'metric':
                widget['properties']['metrics'][0][3] = brokerName
                widget['properties']['metrics'][0][5] = topicName
                widget['properties']['region'] = brokerRegion
        cw.put_dashboard(DashboardName=getObjectDashboardName(topicName), DashboardBody=json.dumps(topicJson))

def lambda_handler(event, context):
    global queue_dashboard_template
    global topic_dashboard_template

    version = '0.2'
    """
    Notes:
    Version 0.1: Initial Release.
    Version 0.2: Add support for topics.                    
    """

    queue_dashboard_template = """
    {
      "widgets": [
        {
          "type": "text",
          "x": 1,
          "y": 25,
          "width": 21,
          "height": 1,
          "properties": {
            "markdown": "\n## Queues\n"
          }
        },
        {
          "type": "metric",
          "x": 1,
          "y": 26,
          "width": 21,
          "height": 6,
          "properties": {
            "metrics": [
              [ "AWS/AmazonMQ", "EnqueueCount", "Broker", "iad-broker-1", "Queue", "TEST.QUEUE" ],
              [ ".", "DequeueCount", ".", ".", ".", ".", { "yAxis": "right" } ]
            ],
            "view": "timeSeries",
            "stacked": false,
            "region": "us-east-1",
            "period": 300,
            "stat": "Average"
          }
        },
        {
          "type": "metric",
          "x": 1,
          "y": 32,
          "width": 21,
          "height": 6,
          "properties": {
            "metrics": [
              [ "AWS/AmazonMQ", "DispatchCount", "Broker", "iad-broker-1", "Queue", "TEST.QUEUE" ],
              [ ".", "InFlightCount", ".", ".", ".", ".", { "yAxis": "right" } ]
            ],
            "view": "timeSeries",
            "stacked": false,
            "region": "us-east-1",
            "stat": "Average",
            "period": 300
          }
        }
      ]
    }
    """

    topic_dashboard_template = """
    {
        "widgets": [
            {
                "type": "metric",
                "x": 0,
                "y": 0,
                "width": 24,
                "height": 6,
                "properties": {
                    "metrics": [
                        [ "AWS/AmazonMQ", "ProducerCount", "Broker", "iad-broker-1", "Topic", "TEST.TOPIC" ],
                        [ ".", "ConsumerCount", ".", ".", ".", "." ]

                    ],
                    "view": "timeSeries",
                    "stacked": false,
                    "region": "us-east-1",
                    "stat": "Average",
                    "period": 300,
                    "title": ""
                }
            },
            {
                "type": "metric",
                "x": 0,
                "y": 6,
                "width": 24,
                "height": 6,
                "properties": {
                    "view": "timeSeries",
                    "stacked": false,
                    "metrics": [
                        [ "AWS/AmazonMQ", "EnqueueCount", "Broker", "iad-broker-1", "Topic", "TEST.TOPIC" ],
                        [ ".", "DispatchCount", ".", ".", ".", "." ],
                        [ ".", "InFlightCount", ".", ".", ".", "." ],
                        [ ".", "DequeueCount", ".", ".", ".", "." ],
                        [ ".", "ExpiredCount", ".", ".", ".", "." ]
                    ],
                    "region": "us-east-1",
                    "period": 300
                }
            },
            {
                "type": "metric",
                "x": 0,
                "y": 12,
                "width": 24,
                "height": 6,
                "properties": {
                    "view": "timeSeries",
                    "stacked": false,
                    "metrics": [
                        [ "AWS/AmazonMQ", "MemoryUsage", "Broker", "iad-broker-1", "Topic", "TEST.TOPIC" ]
                    ],
                    "region": "us-east-1"
                }
            },
            {
                "type": "metric",
                "x": 0,
                "y": 18,
                "width": 24,
                "height": 6,
                "properties": {
                    "view": "timeSeries",
                    "stacked": false,
                    "metrics": [
                        [ "AWS/AmazonMQ", "EnqueueTime", "Broker", "iad-broker-1", "Topic", "TEST.TOPIC" ]
                    ],
                    "region": "us-east-1"
                }
            }
        ]
    }
    """

    brokerList = mq.list_brokers()
    for broker in brokerList['BrokerSummaries']:
        brokerName = broker['BrokerName']
        brokerRegion = broker['BrokerArn'].split(":")[3]
        deploymentMode = broker['DeploymentMode']
        if deploymentMode == 'SINGLE_INSTANCE':
            generateObjectDashboard(brokerName, brokerRegion)
        else:
            generateObjectDashboard(brokerName + "-1", brokerRegion)
            generateObjectDashboard(brokerName + "-2", brokerRegion)
