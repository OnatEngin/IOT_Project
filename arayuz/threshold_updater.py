import os
import boto3

def update_threshold(metric_name, threshold_value, unit):
        
    try:
        # Validate input
        if not threshold_value or not metric_name:
            return False, "Metric name and threshold value are required"
            
        # Try to convert threshold to float
        try:
            threshold_float = float(threshold_value)
        except ValueError:
            return False, f"Invalid threshold value: {threshold_value}. Must be a number."

        cw = boto3.client(
            'cloudwatch',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name='eu-west-1'
        )

        # Log what we're trying to do
        print(f"Setting alarm for {metric_name} with threshold {threshold_float}")

        cw.put_metric_alarm(
            AlarmName=f'{metric_name}_Alarm',
            AlarmDescription='Updated via UI',
            ActionsEnabled=True,
            AlarmActions=os.getenv("AlarmActions"),
            OKActions=os.getenv("OKActions"),
            MetricName=metric_name,
            Namespace='SensorMetrics',
            Statistic='Maximum',
            Dimensions=[
                {'Name': 'Type', 'Value': metric_name.lower()},
                {'Name': 'Unit', 'Value': unit }
            ],
            Period=10,
            EvaluationPeriods=1,
            Threshold=threshold_float,
            ComparisonOperator='GreaterThanThreshold',
            TreatMissingData='notBreaching'
        )

        # If we got here, it worked
        return True, f"Successfully set {metric_name} threshold to {threshold_float}"
    
    except boto3.exceptions.Boto3Error as e:
        # Handle AWS service errors
        print(f"AWS Error setting threshold: {e}")
        return False, f"AWS Error: {str(e)}"
    except Exception as e:
        # Handle any other errors
        print(f"Unexpected error setting threshold: {type(e).__name__}: {e}")
        return False, f"Error: {str(e)}"
