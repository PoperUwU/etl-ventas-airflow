FROM apache/airflow:3.3.2-python3.12

COPY requirements.txt constraints-3.12.txt /opt/airflow/
RUN pip install --no-cache-dir "apache-airflow==3.3.2" \
    --constraint /opt/airflow/constraints-3.12.txt \
    --requirement /opt/airflow/requirements.txt
