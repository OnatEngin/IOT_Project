import json
import boto3
from datetime import datetime, timezone

cloudwatch = boto3.client('cloudwatch')

# CloudWatch'ın desteklediği birimlere haritalama
CW_UNIT_MAP = {
    'celsius': 'None',        # CW'da Celsius yok; ölçeklenmemiş sayısal veri
    'percent': 'Percent',
    'voltage': 'None',        # CW'da Volts yok; ölçeklenmemiş sayısal veri
    'kelvin': 'None',
    'cm3': 'None',
    'amper': 'None',          # CW'da Ampere yok; ölçeklenmemiş sayısal veri
    # gerekirse buraya başka birimler ekleyin
}

def lambda_handler(event, context):
    try:
        # Eğer event body JSON string olarak geliyorsa:
        payload = event.get('body')
        if isinstance(payload, str):
            data = json.loads(payload)
        else:
            data = event

        metric_type = data.get('type')      # e.g. "temperature"
        unit        = data.get('unit')      # e.g. "celsius"
        timestamp   = data.get('timestamp') # e.g. 1747738647
        value       = data.get('value')     # e.g. 28.53

        # Gerekli alanların varlığını kontrol
        if not all([metric_type, unit, timestamp, value]):
            raise ValueError(f"Missing one of required fields: {data}")

        # MetricName olarak türü büyük harfle başlatılmış kullanıyoruz
        metric_name = metric_type.title().replace('_', ' ')  # "Electric_Voltage" -> "Electric Voltage"

        # CW birimine çeviri; yoksa 'None' (ölçeklenmemiş) kullan
        cw_unit = CW_UNIT_MAP.get(unit.lower(), 'None')

        # Unix timestamp'i UTC datetime objesine çevir
        ts = datetime.fromtimestamp(timestamp, tz=timezone.utc)

        # CloudWatch'a metric gönder
        cloudwatch.put_metric_data(
            Namespace='SensorMetrics',   # dilediğiniz namespace
            MetricData=[
                {
                    'MetricName': metric_name,
                    'Dimensions': [
                        {'Name': 'Unit', 'Value': unit},
                        {'Name': 'Type', 'Value': metric_type},
                    ],
                    'Timestamp': ts,
                    'Value': value,
                    'Unit': cw_unit
                },
            ]
        )

        return {
            'statusCode': 200,
            'body': json.dumps(f"Metric {metric_name} ({value} {unit}) published")
        }

    except Exception as e:
        print("Error publishing metric:", e)
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error: {e}")
        }
