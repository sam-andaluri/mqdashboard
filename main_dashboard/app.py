import json
import boto3
import os

# AWS API clients
mq = boto3.client(service_name='mq', region_name=os.environ['MQ_REGION'])
cw = boto3.client(service_name='cloudwatch', region_name=os.environ['MQ_REGION'])

# Generates a CW dashboard URL markdown for a given broker.
def generateBrokerURLMd(brokerName, brokerRegion, isSingle):
    retval = ""
    if isSingle:
        retval = """[""" + brokerName + """](https://console.aws.amazon.com/cloudwatch/home?region=""" + brokerRegion + """#dashboards:name=""" + brokerName + """)\n\n"""
    else:
        retval = brokerName + """ [Primary](https://console.aws.amazon.com/cloudwatch/home?region=""" + brokerRegion + """#dashboards:name=""" + brokerName + """-1) [Standby](https://console.aws.amazon.com/cloudwatch/home?region=""" + brokerRegion + """#dashboards:name=""" + brokerName + """-2)\n\n"""
    return retval


def lambda_handler(event, context):
    global dashboard_template

    version = '0.3'
    """
    Notes:
    Version 0.1: Initial Release.
    Version 0.2: Add support for region. 
    Version 0.3: Add support for customer name customization.                   
    """

    dashboard_template = """{
        "widgets": [
        {
          "type": "text",
          "x": 1,
          "y": 0,
          "width": 21,
          "height": 3,
          "properties": {
            "markdown": "\n# %s MQ Operations\n## Playbook\nThis is a sample dashboard that customers can customize to suit their needs. This dashboard demonstrates how different metrics can be charted to provide meaningful insights for monitoring AmazonMQ instances.\n\n"
          }
        },
        {
          "type": "text",
          "x": 1,
          "y": 6,
          "width": 21,
          "height": 6,
          "properties": {
            "markdown": "\n## Broker Health\n"
          }
        }]
    }"""

    brokerUrlsMd = """## Brokers\n\n"""
    brokerList = mq.list_brokers()
    for broker in brokerList['BrokerSummaries']:
        brokerName = broker['BrokerName']
        brokerRegion = broker['BrokerArn'].split(":")[3]
        deploymentMode = broker['DeploymentMode']
        # For a single instance broker, generate single URL for the broker.
        # For Active/Standby broker, generate a Primary and Standby link for the broker.
        if deploymentMode == 'SINGLE_INSTANCE':
            brokerUrlsMd += generateBrokerURLMd(brokerName, brokerRegion, True)
        else:
            brokerUrlsMd += generateBrokerURLMd(brokerName, brokerRegion, False)
    dashboard_template = dashboard_template % os.environ['CUSTOMER_NAME']
    mqJson = json.loads(dashboard_template, strict=False)
    mqJson['widgets'][1]['properties']['markdown'] = brokerUrlsMd
    cw.put_dashboard(DashboardName="AmazonMQ-" + os.environ['MQ_REGION'], DashboardBody=json.dumps(mqJson))
