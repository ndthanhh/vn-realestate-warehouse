from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'admin',
    'start_date': datetime(2026, 4, 25),
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

# DAG này chạy 15 phút/lần - Chỉ lo cào Link từ danh sách tỉnh
with DAG(
    'dag_crawl_links',
    default_args=default_args,
    description='Thu thap link BDS tu batdongsan.com.vn (15 phut/lan)',
    schedule_interval='*/15 * * * *',
    catchup=False,
    tags=['realestate', 'crawler', 'links'],
) as dag:

    # Cào link từ các tỉnh theo cơ chế xoay vòng
    crawl_links = BashOperator(
        task_id='crawl_links',
        bash_command='xvfb-run -a python /opt/crawler/crawl_link.py',
    )
