from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner' : 'admin',
    'start_date' : datetime(2024, 1, 1),
    'retries' :1,
    'retry_delay' :timedelta(minutes=2),
}

with DAG(
    'realestate_elt_pipeline',
    default_args=default_args,
    schedule_interval='@daily',
    catchup=False,
    tags=['realestate', 'automation'],
) as dag:
    # Task 1: Cào Link (Chạy qua màn hình ảo Xvfb)
    crawl_links = BashOperator(
        task_id='crawl_links',
        bash_command='xvfb-run -a python /opt/crawler/crawl_link.py'
    )
    # Task 2: Cào Chi Tiết (Chạy qua màn hình ảo Xvfb)
    crawl_detail = BashOperator(
        task_id='crawl_detail',
        bash_command='xvfb-run -a python /opt/crawler/crawl_detail.py'
    )
    # Task 3: Spark Bronze -> Silver
    bronze_to_silver = BashOperator(
        task_id='bronze_to_silver',
        bash_command="docker exec vn-realestate-warehouse-spark-master-1 spark-submit --master spark://spark-master:7077 --packages org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262 /opt/bitnami/spark/spark_jobs/etl_bronze_to_sliver.py"
    )
    # Task 4: Spark Silver -> Gold (Postgres)
    silver_to_gold = BashOperator(
        task_id='silver_to_gold',
        bash_command="docker exec vn-realestate-warehouse-spark-master-1 spark-submit --master spark://spark-master:7077 --packages org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262,org.postgresql:postgresql:42.6.0 /opt/bitnami/spark/spark_jobs/etl_silver_to_gold.py"
    )

    crawl_links >> crawl_detail >> bronze_to_silver >> silver_to_gold
