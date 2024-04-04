import os
import boto3
from datetime import date
import requests

def assume_role(role_arn, session_name):
    # Create a new STS client
    sts_client = boto3.client('sts')

    # Assume the IAM role
    response = sts_client.assume_role(
        RoleArn=role_arn,
        RoleSessionName=session_name
    )

    # Extract temporary credentials
    credentials = response['Credentials']

    # Create a Boto3 session with the temporary credentials
    session = boto3.Session(
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken']
    )

    return session

def get_billed_resources():
    role_arn = 'arn:aws:iam::420779746987:role/RoleCostExplorerAPI'
    session_name = 'AssumedRoleSession'

    # Assume the IAM role
    session = assume_role(role_arn, session_name)

    # Accessing Cost Explorer API
    client = session.client('ce')

    # StartDate = 1st date of current month, EndDate = Todays date
    start_date = str(date(year=date.today().year, month=date.today().month, day=1).strftime('%Y-%m-%d'))
    end_date = str(date.today())

    print(f'StartDate:{start_date} - EndDate:{end_date}\n')

    # The get_cost_and_usage operation is a part of the AWS Cost Explorer API, which allows you to programmatically retrieve cost and usage data for your AWS accounts.
    response = client.get_cost_and_usage(
        TimePeriod={
            'Start': start_date,
            'End': end_date
        },
        Granularity='MONTHLY',
        Metrics=['UnblendedCost'],
        Filter={
            "Not": {
                'Dimensions': {
                    'Key': 'RECORD_TYPE',
                    'Values': ['Credit', 'Refund']
                }
            }
        },
        GroupBy=[
            {
                'Type': 'DIMENSION',
                'Key': 'SERVICE'
            }
        ]
    )

    mydict = response
    resource_name = []
    resource_cost = []

    total_resources_active = len(mydict['ResultsByTime'][0]['Groups'])

    for i in range(total_resources_active):
        a = (mydict['ResultsByTime'][0]['Groups'][i].values())
        b = list(a)
        resource_name.append(b[0][0])
        resource_cost.append(float(b[1]['UnblendedCost']['Amount']))

    dict0 = {}

    for i in range(total_resources_active):
        dict0[resource_name[i]] = resource_cost[i]

    # Filter out resources with a cost of $0.00
    billed_resources = {k: v for k, v in dict0.items() if v > 0}

    return billed_resources

def lambda_handler(event, context):
    # Replace TELEGRAM_API_TOKEN with your actual Telegram API token
    TELEGRAM_API_TOKEN = os.getenv('TELEGRAM_API_TOKEN')

    # Retrieve chat ID from environment variable
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

    # Retrieve billing information
    billed_resources = get_billed_resources()

    # Prepare message to send to Telegram
    message = "Current Billed Resources of this month:\n\n"
    for resource, cost in billed_resources.items():
        message += f"{resource}: ${cost:.2f}\n"

    # Send message to Telegram
    url = f'https://api.telegram.org/bot{TELEGRAM_API_TOKEN}/sendMessage'
    params = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'  # Specify MarkdownV2 parsing mode
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"Failed to send message to Telegram. Status code: {response.status_code}")
    else:
        print("Message sent successfully to Telegram")

    return {"statusCode": 200}
