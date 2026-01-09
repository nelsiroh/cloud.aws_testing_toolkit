import boto3
from botocore.exceptions import BotoCoreError, ClientError
from datetime import datetime, timedelta

# Initialize AWS clients
ec2_client = boto3.client('ec2', region_name='us-east-2')
cloudwatch_client = boto3.client('cloudwatch', region_name='us-east-2')

def get_instances_with_tag(tag_key, tag_value):
    """Fetch EC2 instances with a specific tag."""
    try:
        response = ec2_client.describe_instances(
            Filters=[
                {'Name': f'tag:{tag_key}', 'Values': [tag_value]},
                {'Name': 'instance-state-name', 'Values': ['running']}
            ]
        )
        instances = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instances.append(instance['InstanceId'])
        return instances
    except (BotoCoreError, ClientError) as error:
        print(f"Error fetching instances with tag {tag_key}={tag_value}: {error}")
        return []

def get_cpu_utilization(instance_id):
    """Fetch the average CPU utilization for the past hour."""
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        response = cloudwatch_client.get_metric_statistics(
            Namespace='AWS/EC2',
            MetricName='CPUUtilization',
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
            StartTime=start_time,
            EndTime=end_time,
            Period=3600,
            Statistics=['Average']
        )
        datapoints = response.get('Datapoints', [])
        if datapoints:
            return datapoints[0]['Average']
        return None
    except (BotoCoreError, ClientError) as error:
        print(f"Error fetching CPU utilization for instance {instance_id}: {error}")
        return None

def stop_instances(instances):
    """Stop EC2 instances."""
    try:
        if instances:
            ec2_client.stop_instances(InstanceIds=instances)
            print(f"Stopped instances: {instances}")
        else:
            print("No instances to stop.")
    except (BotoCoreError, ClientError) as error:
        print(f"Error stopping instances: {error}")

def main():
    try:
        # Step 1: Get instances with the tag auto_shutdown=true
        instances = get_instances_with_tag('auto_shutdown', 'true')
        print(f"Instances with auto_shutdown=true: {instances}")

        # Step 2: Check CPU utilization and stop instances if below threshold
        instances_to_stop = []
        for instance_id in instances:
            cpu_utilization = get_cpu_utilization(instance_id)
            if cpu_utilization is not None and cpu_utilization < 5:
                print(f"Instance {instance_id} has low CPU utilization: {cpu_utilization}%")
                instances_to_stop.append(instance_id)
            else:
                print(f"Instance {instance_id} has sufficient CPU utilization: {cpu_utilization}%")

        # Step 3: Stop instances
        stop_instances(instances_to_stop)

    except Exception as error:
        print(f"An unexpected error occurred: {error}")

if __name__ == "__main__":
    main()