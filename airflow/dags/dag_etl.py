from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'admin',
    'start_date': datetime(2026, 4, 25),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# DAG này chạy 1 lần/ngày lúc 2h sáng - Xử lý nặng bằng Spark
with DAG(
    'dag_etl',
    default_args=default_args,
    description='ETL Bronze -> Silver -> Gold (1 lan/ngay luc 2h sang)',
    schedule_interval='0 2 * * *',
    catchup=False,
    tags=['realestate', 'etl', 'spark'],
) as dag:

    # Task 1: Spark Bronze -> Silver 
    bronze_to_silver = BashOperator(
        task_id='bronze_to_silver',
        bash_command='docker exec vn-realestate-warehouse-spark-master-1 '
                     'spark-submit --master spark://spark-master:7077 '
                     '--packages org.apache.hadoop:hadoop-aws:3.3.4,'
                     'com.amazonaws:aws-java-sdk-bundle:1.12.262 '
                     '/opt/bitnami/spark/spark_jobs/etl_bronze_to_silver.py',
    )

    # Task 2: Spark Silver -> Gold
    silver_to_gold = BashOperator(
        task_id='silver_to_gold',
        bash_command='docker exec vn-realestate-warehouse-spark-master-1 '
                     'spark-submit --master spark://spark-master:7077 '
                     '--packages org.apache.hadoop:hadoop-aws:3.3.4,'
                     'com.amazonaws:aws-java-sdk-bundle:1.12.262,'
                     'org.postgresql:postgresql:42.6.0 '
                     '/opt/bitnami/spark/spark_jobs/etl_silver_to_gold.py',
    )

    bronze_to_silver >> silver_to_gold
