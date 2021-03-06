import json
import boto3
import os

# AWS API clients
mq = boto3.client(service_name='mq', region_name=os.environ['MQ_REGION'])
cw = boto3.client(service_name='cloudwatch', region_name=os.environ['MQ_REGION'])
ssm = boto3.client(service_name='ssm', region_name=os.environ['MQ_REGION'])

topicArn = os.environ['SNS_TOPIC_ARN']

# Dashboard names can only have a dash or underscore.
def getObjectDashboardName(objectName):
    return objectName.replace(".", "-")

# Generate a CW dashboard URL markdown for a given queue
def generateObjectURLMd(objectName, displayName, brokerName, brokerRegion):
    returnVal = """"""
    if brokerName is None:
        returnVal = """[""" + displayName + """](https://console.aws.amazon.com/cloudwatch/home?region=""" + brokerRegion + """#dashboards:name=""" + getObjectDashboardName(
        objectName) + """)\n\n"""
    else:
        returnVal = """[""" + displayName + """](https://console.aws.amazon.com/cloudwatch/home?region=""" + brokerRegion + """#dashboards:name=""" + getObjectDashboardName(
        objectName) + """-""" + brokerName + """)\n\n"""
    return returnVal

# Given a broker, enumerate queues and topics for that broker
def getListOfQueuesAndTopics(brokerName, queueList, topicList):
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
                        continue
                    else:
                        topicList.add(topicName)
            elif dimensions['Name'] == 'Queue':
                queueList.add(dimensions['Value'])

# Generates a CW dashboard for each broker including a list of queues and topics
def generateBrokerDashboard(brokerName, brokerRegion):
    # Init queueList set.
    queueList = set()
    topicList = set()
    queueSummary = list()
    topicSummary = list()
    queueSummaryWidget = dict()
    topicSummaryWidget = dict()

    # MQ client does not have API for listing queues and topics.
    # Use the CW client to get the queue and topic list.
    getListOfQueuesAndTopics(brokerName, queueList, topicList)

    # Initialize the queue list markdown
    objectListMd = """\n ## Broker metrics for **%s**\n\n ## Queues \n %s \n\n"""

    yPos = 0
    for queueName in queueList:
        # Add queue and topic dashboard URLs to markdown
        objectListMd += generateObjectURLMd(queueName, queueName, brokerName, brokerRegion)
        summaryJson = json.loads(queues_summary_template, strict=False)
        yPos += 3
        summaryJson['y'] += yPos
        summaryJson['properties']['metrics'][0][3] = brokerName
        summaryJson['properties']['metrics'][0][5] = queueName
        summaryJson['properties']['region'] = brokerRegion
        summaryJson['properties']['title'] = queueName
        queueSummary.append(summaryJson)


    objectListMd += """\n ## Topics \n %s \n\n"""

    yPos = 0
    for topicName in topicList:
        # Add queue and topic dashboard URLs to markdown
        objectListMd += generateObjectURLMd(topicName, topicName, brokerName, brokerRegion)
        summaryJson = json.loads(topics_summary_template, strict=False)
        yPos += 3
        summaryJson['y'] += yPos
        summaryJson['properties']['metrics'][0][3] = brokerName
        summaryJson['properties']['metrics'][0][5] = topicName
        summaryJson['properties']['region'] = brokerRegion
        summaryJson['properties']['title'] = topicName
        topicSummary.append(summaryJson)

    queueSummaryWidget["widgets"] = queueSummary
    topicSummaryWidget['widgets'] = topicSummary

    if len(queueSummary) > 0:
        cw.put_dashboard(DashboardName=brokerName + '-QueueSummary', DashboardBody=json.dumps(queueSummaryWidget))
    if len(topicSummary) > 0:
        cw.put_dashboard(DashboardName=brokerName + '-TopicSummary', DashboardBody=json.dumps(topicSummaryWidget))

    finalMd = objectListMd % (brokerName, generateObjectURLMd(brokerName + '-QueueSummary', "Summary of Queues", None, brokerRegion), generateObjectURLMd(brokerName + '-TopicSummary', "Summary of Topics", None, brokerRegion))

    # Read the broker dashboard template to generate a new dashboard for each broker
    # A separate dahsboard is generated for each broker and link to this dashboard is added
    # to AmazonMQ dashboard.
    brokerJson = json.loads(broker_dashboard_template, strict=False)
    brokerJson['widgets'][0]['properties']['markdown'] = finalMd
    for widget in brokerJson['widgets']:
        if widget['type'] == 'metric':
            widget['properties']['metrics'][0][3] = brokerName
            widget['properties']['region'] = brokerRegion
    cw.put_dashboard(DashboardName=brokerName, DashboardBody=json.dumps(brokerJson))

def put_broker_alarms(brokerName):
    cw.put_metric_alarm(
        AlarmName='BrokerHeapUsage-'+ brokerName,
        ComparisonOperator='GreaterThanThreshold',
        EvaluationPeriods=5,
        MetricName='HeapUsage',
        Namespace='AWS/AmazonMQ',
        Period=60,
        Statistic='Average',
        Threshold=70.0,
        ActionsEnabled=True,
        OKActions=[
            topicArn,
        ],
        AlarmActions=[
            topicArn,
        ],
        AlarmDescription='Heap usage exceeded 80% for broker ' + brokerName,
        Dimensions=[
            {
                'Name': 'Broker',
                'Value': brokerName
            }
        ],
        Unit='Percent'
    )
    cw.put_metric_alarm(
        AlarmName='BrokerStoreUsage-'+ brokerName,
        ComparisonOperator='GreaterThanThreshold',
        EvaluationPeriods=5,
        MetricName='StorePercentUsage',
        Namespace='AWS/AmazonMQ',
        Period=60,
        Statistic='Average',
        Threshold=70.0,
        ActionsEnabled=True,
        OKActions=[
            topicArn,
        ],
        AlarmActions=[
            topicArn,
        ],
        AlarmDescription='Storage usage exceeded 80% for broker ' + brokerName,
        Dimensions=[
            {
                'Name': 'Broker',
                'Value': brokerName
            },
        ],
        Unit='Percent'
    )
    cw.put_metric_alarm(
        AlarmName='BrokerCPUUtilization-'+ brokerName,
        ComparisonOperator='GreaterThanThreshold',
        EvaluationPeriods=5,
        MetricName='CpuUtilization',
        Namespace='AWS/AmazonMQ',
        Period=60,
        Statistic='Average',
        Threshold=70.0,
        ActionsEnabled=True,
        OKActions=[
            topicArn,
        ],
        AlarmActions=[
            topicArn,
        ],
        AlarmDescription='Heap usage exceeded 80% for broker ' + brokerName,
        Dimensions=[
            {
                'Name': 'Broker',
                'Value': brokerName
            },
        ],
        Unit='Percent'
    )


def delete_broker_alarms(brokerName):
    cw.delete_alarms(
        AlarmNames=[
            'BrokerHeapUsage-'+ brokerName, 'BrokerStoreUsage-'+ brokerName, 'BrokerCPUUtilization-'+ brokerName
        ]
    )


def lambda_handler(event, context):
    global broker_dashboard_template
    global queues_summary_template
    global topics_summary_template
    global provisionAlarms

    version = '0.4'
    """
    Notes:
    Version 0.1: Initial Release. No support for topics yet.  
    Version 0.2: Added support for topics. Added queue and topics summary dashboards. 
    Version 0.3: Paramterize the dashboard.
    Version 0.4: Add broker alarms.                 
    """

    queues_summary_template = """
    {
        "type": "metric",
        "x": 0,
        "y": 0,
        "width": 24,
        "height": 3,
        "properties": {
            "view": "singleValue",
            "metrics": [
                [ "AWS/AmazonMQ", "ProducerCount", "Broker", "iad-broker-1", "Queue", "TEST.QUEUE" ],
                [ ".", "QueueSize", ".", ".", ".", "." ],
                [ ".", "ConsumerCount", ".", ".", ".", "." ]
            ],
            "region": "us-east-1",
            "period": 60,
            "title": "TEST.QUEUE"
        }
    }
    """

    topics_summary_template = """
    {
        "type": "metric",
        "x": 0,
        "y": 0,
        "width": 24,
        "height": 3,
        "properties": {
            "view": "singleValue",
            "metrics": [
                [ "AWS/AmazonMQ", "ProducerCount", "Broker", "iad-broker-1", "Topic", "TEST.TOPIC" ],
                [ ".", "EnqueueCount", ".", ".", ".", "." ],
                [ ".", "DequeueCount", ".", ".", ".", "." ],                    
                [ ".", "ConsumerCount", ".", ".", ".", "." ]
            ],
            "region": "us-east-1",
            "period": 60,
            "title": "TEST.TOPIC"
        }
    }
    """

    broker_dashboard_template = """
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
            "period": 60,
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
            "period": 60,
            "stat": "Average"
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
        if provisionAlarms:
            put_broker_alarms(brokerName)
        else:
            delete_broker_alarms(brokerName)

        if deploymentMode == 'SINGLE_INSTANCE':
            generateBrokerDashboard(brokerName + "-1", brokerRegion)
        else:
            generateBrokerDashboard(brokerName + "-1", brokerRegion)
            generateBrokerDashboard(brokerName + "-2", brokerRegion)
