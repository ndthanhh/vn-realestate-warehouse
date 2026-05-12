from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'admin',
    'start_date': datetime(2026, 4, 25),
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

# DAG này chạy 5 phút/lần - Lo đi lấy chi tiết 1 tin duy nhất
with DAG(
    'dag_crawl_details',
    default_args=default_args,
    description='Thu thap chi tiet tung tin BDS (5 phut/lan)',
    schedule_interval='*/5 * * * *',
    catchup=False,
    tags=['realestate', 'crawler', 'details'],
) as dag:

    # Lấy thông tin chi tiết của 1 link đang chờ
    crawl_details = BashOperator(
        task_id='crawl_details',
        bash_command='xvfb-run -a python /opt/crawler/crawl_detail.py',
    )
