import boto3
from flask import Flask, render_template, request
import plotly.graph_objects as go

from cloudwatch_fetcher import get_cloudwatch_metrics
from threshold_updater import update_threshold

app = Flask(__name__)

def generate_plot(timestamps, values, threshold=None, label='Metric', unit=''):
    # Eğer timestamps boşsa hata vermesin
    times = [ts.strftime('%H:%M') for ts in timestamps]
    date_str = timestamps[0].strftime('%Y-%m-%d') if timestamps else "No data"

    fig = go.Figure()

    # Ana çizgi
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=values,
        mode='lines+markers',
        name=label,
        line=dict(width=2),
        marker=dict(size=8)
    ))

    # Threshold ve aşan noktalar
    if threshold is not None and threshold != '':
        tval = float(threshold)
        exceed_x = [t for t, v in zip(timestamps, values) if v > tval]
        exceed_y = [v for v in values if v > tval]

        if exceed_x:
            fig.add_trace(go.Scatter(
                x=exceed_x,
                y=exceed_y,
                mode='markers',
                name=f'{label} > {tval}{unit}',
                marker=dict(size=10, color='red', symbol='circle')
            ))

        # Threshold çizgisi
        fig.add_shape(
            type="line",
            x0=timestamps[0] if timestamps else None,
            y0=tval, x1=timestamps[-1] if timestamps else None,
            y1=tval,
            line=dict(color="red", width=2, dash="dash")
        )
        fig.add_annotation(
            x=timestamps[0] if timestamps else None,
            y=tval,
            text=f"Threshold: {tval}{unit}",
            showarrow=False, yshift=10, font=dict(color="red")
        )

    fig.update_layout(
        title=f"{label} Over Time – {date_str}",
        xaxis_title="Time",
        yaxis_title=f"{label} ({unit})",
        plot_bgcolor='white',
        hovermode='closest',
        margin=dict(l=40, r=40, t=60, b=40),
        height=400, width=800
    )

    return fig.to_html(include_plotlyjs='cdn', full_html=False)

@app.route('/', methods=['GET', 'POST'])
def index():
    error_message = success_message = None

    # Varsayılan threshold’lar
    current_threshold_temp = 30.0
    current_threshold_hum = 40.0

    if request.method == 'POST':
        # Form’dan gelen değerler
        t_temp = request.form.get('threshold_temperature')
        t_hum = request.form.get('threshold_humidity')
        try:
            if t_temp and float(t_temp) != current_threshold_temp:
                current_threshold_temp = t_temp
                update_threshold('Temperature', current_threshold_temp, 'celsius')
            if t_hum and float(t_hum) != current_threshold_hum:
                current_threshold_hum = t_hum
                update_threshold('Humidity', current_threshold_hum, 'cm3')
            success_message = "Threshold is successfully updated."
        except Exception as e:
            error_message = f"Threshold güncelleme hatası: {e}"

    # CloudWatch’tan veri çekme
    try:
        namespace = 'SensorMetrics'
        dims_temp = [
        {'Name': 'Type', 'Value': 'temperature'},
        {'Name': 'Unit', 'Value': 'celsius'}
    ]
        dims_hum = [
        {'Name': 'Type', 'Value': 'humidity'},
        {'Name': 'Unit', 'Value': 'cm3'}
    ]

        timestamps, vals_temp = get_cloudwatch_metrics(namespace, 'Temperature', dims_temp)
        _,           vals_hum  = get_cloudwatch_metrics(namespace, 'Humidity',    dims_hum)

        if not timestamps:
            error_message = "The Data Fetcher encountered an error."
    except Exception as e:
        timestamps, vals_temp, vals_hum = [], [], []
        error_message = f"Metric fetch hatası: {e}"

    # Grafik HTML’leri
    plot_temp = generate_plot(timestamps, vals_temp, current_threshold_temp, label='Temperature', unit='°C')
    plot_hum  = generate_plot(timestamps, vals_hum,  current_threshold_hum,  label='Humidity',    unit='%')

    # Eşik aşımlarını sayma
    count_temp = sum(1 for v in vals_temp if v > float(current_threshold_temp)) if timestamps else 0
    count_hum  = sum(1 for v in vals_hum  if v > float(current_threshold_hum))  if timestamps else 0

    return render_template(
        'index.html',
        plot_temp=plot_temp,
        plot_hum=plot_hum,
        current_threshold_temp=current_threshold_temp,
        current_threshold_hum=current_threshold_hum,
        count_temp=count_temp,
        count_hum=count_hum,
        error_message=error_message,
        success_message=success_message,
        img_path='/static/logo.png'
    )

if __name__ == '__main__':
    app.run(debug=True)
