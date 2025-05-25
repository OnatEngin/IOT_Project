import os
import boto3
from datetime import datetime, timezone, timedelta

def get_cloudwatch_metrics(namespace, metric_name, dimensions, period=60, stat='Average'):
    try:
        cloudwatch = boto3.client(
            'cloudwatch',
            region_name='eu-west-1',
            aws_access_key = os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        )

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=24)

        # Add debug print statements
        print(f"Fetching with: Namespace={namespace}, MetricName={metric_name}")
        print(f"Dimensions: {dimensions}")
        print(f"Period: {period}, Stat: {stat}")

        response = cloudwatch.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=dimensions,
            StartTime=start_time,
            EndTime=end_time,
            Period=period,
            Statistics=[stat]
        )

        # Print the raw response for debugging
        print(f"Raw CloudWatch response: {response}")

        datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])
        timestamps = [point['Timestamp'] for point in datapoints]
        values = [point[stat] for point in datapoints]

        print("Gelen veri sayısı:", len(timestamps))
        print("Timestamps:", timestamps)
        print("Values:", values)

        return timestamps, values
    
    except boto3.exceptions.Boto3Error as e:
        # Handle specific AWS service errors
        print(f"AWS Service Error: {e}")
        return [], []
    except KeyError as e:
        # Handle missing keys in the response
        print(f"Missing key in response: {e}")
        return [], []
    except Exception as e:
        # Catch any other unexpected errors
        print(f"Unexpected error fetching metrics: {type(e).__name__}: {e}")
        return [], []
