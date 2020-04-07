import copy
import json
import boto3
import os

# AWS API clients
mq = boto3.client(service_name='mq', region_name=os.environ['MQ_REGION'])
cw = boto3.client(service_name='cloudwatch', region_name=os.environ['MQ_REGION'])
ssm = boto3.client(service_name='ssm', region_name=os.environ['MQ_REGION'])

topicArn = os.environ['SNS_TOPIC_ARN']

# Dashboard names can only have a dash or underscore.
def getObjectDashboardName(objectName, brokerName):
    return objectName.replace(".", "-") + "-" + brokerName

# Given a broker, enumerate queues and topics for that broker
def getListOfQueuesAndTopics(brokerName, queueList, topicList, advList):
    # Get a list of metrics for AmazonMQ and a broker. This would help enumerate queues and topics
    resp = cw.list_metrics(Namespace="AWS/AmazonMQ", Dimensions=[{'Name': 'Broker', 'Value': brokerName}])
    for metrics in resp['Metrics']:
        for dimensions in metrics['Dimensions']:
            if dimensions['Name'] == 'Topic':
                topicName = dimensions['Value']
                if os.environ['INCLUDE_ADVISORY'] == 'YES':
                    topicList.add(topicName)
                else:
                    if 'Advisory' in topicName:
                        advList.add(getObjectDashboardName(topicName, brokerName))
                    else:
                        topicList.add(topicName)
            elif dimensions['Name'] == 'Queue':
                queueList.add(dimensions['Value'])

def put_topic_alarm(brokerName, topicName):
    cw.put_metric_alarm(
        AlarmName='NoConsumer-'+ topicName,
        ComparisonOperator='LessThanOrEqualToThreshold',
        EvaluationPeriods=2,
        MetricName='ConsumerCount',
        Namespace='AWS/AmazonMQ',
        Period=60,
        Statistic='SampleCount',
        Threshold=0,
        ActionsEnabled=True,
        AlarmActions=[
            topicArn,
        ],
        AlarmDescription='No consumers for ' + topicName,
        Dimensions=[
            {
                'Name': 'Broker',
                'Value': brokerName
            },
            {
                'Name': 'Topic',
                'Value': topicName
            },
        ],
        Unit='Count'
    )

def put_queue_alarm(brokerName, queueName):
    cw.put_metric_alarm(
        AlarmName='NoConsumer-'+ queueName,
        ComparisonOperator='LessThanOrEqualToThreshold',
        EvaluationPeriods=2,
        MetricName='ConsumerCount',
        Namespace='AWS/AmazonMQ',
        Period=60,
        Statistic='SampleCount',
        Threshold=0,
        ActionsEnabled=True,
        AlarmActions=[
            topicArn,
        ],
        AlarmDescription='No consumers for ' + queueName,
        Dimensions=[
            {
                'Name': 'Broker',
                'Value': brokerName
            },
            {
                'Name': 'Queue',
                'Value': queueName
            },
        ],
        Unit='Count'
    )

def delete_topic_alarm(brokerName, topicName):
    cw.delete_alarms(
        AlarmNames=[
            'NoConsumer-'+ topicName,
        ]
    )


def delete_queue_alarm(brokerName, queueName):
    cw.delete_alarms(
        AlarmNames=[
            'NoConsumer-'+ queueName,
        ]
    )

# Generates a CW dashboard for each broker including a list of queues and topics
def generateObjectDashboard(brokerName, brokerRegion):
    # Init queueList set.
    queueList = set()
    topicList = set()
    advList = set()

    # MQ client does not have API for listing queues and topics.
    # Use the CW client to get the queue and topic list.
    getListOfQueuesAndTopics(brokerName, queueList, topicList, advList)

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
        if provisionAlarms:
            put_queue_alarm(brokerName, queueName)
        else:
            delete_queue_alarm(brokerName, queueName)
        cw.put_dashboard(DashboardName=getObjectDashboardName(queueName, brokerName), DashboardBody=json.dumps(queueJson))

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
        if provisionAlarms:
            put_topic_alarm(brokerName, topicName)
        else:
            delete_topic_alarm(brokerName, topicName)
        cw.put_dashboard(DashboardName=getObjectDashboardName(topicName, brokerName), DashboardBody=json.dumps(topicJson))

def lambda_handler(event, context):
    global queue_dashboard_template
    global topic_dashboard_template
    global provisionAlarms

    version = '0.4'
    """
    Notes:
    Version 0.1: Initial Release.
    Version 0.2: Add support for topics. 
    Version 0.3: Parameterize the dashboard.
    Version 0.4: Add queue and topic alarm.                   
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
            "period": 60,
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
            "period": 60
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
                    "period": 60,
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
                    "period": 60
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

    try:
        provisionAlarmsOverride = ssm.get_parameter(Name='MQAlarmToggle', WithDecryption=False)['Parameter']['Value']
        if provisionAlarmsOverride == "YES":
            provisionAlarms = True
        else:
            provisionAlarms = False
    except:
        if os.environ['PROVISION_ALARMS'] == "YES":
            provisionAlarms = True
        else:
            provisionAlarms = False

    brokerList = mq.list_brokers()
    for broker in brokerList['BrokerSummaries']:
        brokerName = broker['BrokerName']
        brokerRegion = broker['BrokerArn'].split(":")[3]
        deploymentMode = broker['DeploymentMode']
        if deploymentMode == 'SINGLE_INSTANCE':
            generateObjectDashboard(brokerName + "-1", brokerRegion)
        else:
            generateObjectDashboard(brokerName + "-1", brokerRegion)
            generateObjectDashboard(brokerName + "-2", brokerRegion)
