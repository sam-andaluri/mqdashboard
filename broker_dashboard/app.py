import json

import boto3

# AWS API clients
mq = boto3.client('mq')
cw = boto3.client('cloudwatch')


# Dashboard names can only have a dash or underscore.
def getQueueDashboardName(queueName):
    return queueName.replace(".", "-")


# Generate a CW dashboard URL markdown for a given queue
def generateQueueURLMd(queueName, brokerRegion):
    return """[""" + queueName + """](https://console.aws.amazon.com/cloudwatch/home?region=""" + brokerRegion + """#dashboards:name=""" + getQueueDashboardName(
        queueName) + """)\n\n"""


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
def generateBrokerDashboard(brokerName, brokerRegion):
    # Init queueList set.
    queueList = set()
    topicList = set()

    # MQ client does not have API for listing queues and topics.
    # Use the CW client to get the queue and topic list.
    getListOfQueuesAndTopics(brokerName, queueList, topicList)

    # Initialize the queue list markdown
    queueListMd = """\n ## Broker metrics for **""" + brokerName + """**\n\n ## Queues \n"""

    for queueName in queueList:
        # Add queue and topic dashboard URLs to markdown
        queueListMd += generateQueueURLMd(queueName, brokerRegion)

    # Read the broker dashboard template to generate a new dashboard for each broker
    # A separate dahsboard is generated for each broker and link to this dashboard is added
    # to AmazonMQ dashboard.
    brokerJson = json.loads(dashboard_template, strict=False)
    brokerJson['widgets'][0]['properties']['markdown'] = queueListMd
    for widget in brokerJson['widgets']:
        if widget['type'] == 'metric':
            widget['properties']['metrics'][0][3] = brokerName
            widget['properties']['region'] = brokerRegion
    cw.put_dashboard(DashboardName=brokerName, DashboardBody=json.dumps(brokerJson))


def lambda_handler(event, context):
    global dashboard_template

    version = '0.1'
    """
    Notes:
    Version 0.1: Initial Release. No support for topics yet.                    
    """

    dashboard_template = """
    {
      "widgets": [
        {
          "type": "text",
          "x": 1,
          "y": 6,
          "width": 21,
          "height": 6,
          "properties": {
            "markdown": "\n## Broker metrics for \n"
          }
        },
        {
          "type": "metric",
          "x": 1,
          "y": 7,
          "width": 21,
          "height": 6,
          "properties": {
            "view": "timeSeries",
            "stacked": false,
            "metrics": [
              [ "AWS/AmazonMQ", "HeapUsage", "Broker", "iad-broker-1" ],
              [ ".", "CpuUtilization", ".", "." ],
              [ ".", "StorePercentUsage", ".", "." ]
            ],
            "region": "us-east-1"
          }
        },
        {
          "type": "metric",
          "x": 1,
          "y": 13,
          "width": 21,
          "height": 6,
          "properties": {
            "metrics": [
              [ "AWS/AmazonMQ", "NetworkIn", "Broker", "iad-broker-1" ],
              [ ".", "NetworkOut", ".", ".", { "yAxis": "right" } ]
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
          "y": 19,
          "width": 21,
          "height": 6,
          "properties": {
            "metrics": [
              [ "AWS/AmazonMQ", "TotalProducerCount", "Broker", "iad-broker-1" ],
              [ ".", "TotalConsumerCount", ".", ".", { "yAxis": "right" } ]
            ],
            "view": "timeSeries",
            "stacked": false,
            "region": "us-east-1",
            "period": 300,
            "stat": "Average"
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
            generateBrokerDashboard(brokerName, brokerRegion)
        else:
            generateBrokerDashboard(brokerName + "-1", brokerRegion)
            generateBrokerDashboard(brokerName + "-2", brokerRegion)
