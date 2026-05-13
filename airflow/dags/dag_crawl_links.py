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
    'dag_crawl_links',
    default_args=default_args,
    description='Crawl real estate links (every 15 min)',
    schedule_interval='*/15 * * * *',
    catchup=False,
    tags=['realestate', 'crawler', 'links'],
) as dag:

    crawl_links = BashOperator(
        task_id='crawl_links',
        bash_command='xvfb-run -a python /opt/crawler/crawl_link.py',
    )
