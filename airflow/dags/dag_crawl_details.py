from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'admin',
    'start_date': datetime(2026, 4, 25),
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

with DAG(
    'dag_crawl_details',
    default_args=default_args,
    description='Crawl real estate details (every 5 min)',
    schedule_interval='*/5 * * * *',
    catchup=False,
    tags=['realestate', 'crawler', 'details'],
) as dag:

    crawl_details = BashOperator(
        task_id='crawl_details',
        bash_command='xvfb-run -a python /opt/crawler/crawl_detail.py',
    )
