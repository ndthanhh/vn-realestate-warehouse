from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp, regexp_replace, lower, when 

def create_spark_session():
    return SparkSession.builder\
        .appName("ETL_Sliver_to_Gold")\
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000")\
        .config("spark.hadoop.fs.s3a.access.key", "minioadmin")\
        .config("spark.hadoop.fs.s3a.secret.key", "minioadmin")\
        .config("spark.hadoop.fs.s3a.path.style.access", "true")\
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")\
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")\
        .getOrCreate()

def main():
    spark = create_spark_session()

    sliver_path = "s3a://realestate/silver/batdongsan/"
    print(f"Dang doc du lieu tu: {sliver_path}")

    try: 
        df_sliver=spark.read.parquet(sliver_path)

        print(f"Dang khu trung lap!")
        df_gold = df_sliver.dropDuplicates(["url"])
        df_gold = df_gold.withColumn("has_legal_docs", when(lower(col("legal_status")).contains("sổ") | lower(col("legal_status")).contains("đỏ")|lower(col("legal_status")).contains("hồng"), 1).otherwise(0))
        df_gold = df_gold.withColumn("num_bedrooms", regexp_replace(col("specs_bedrooms_raw"), "[^0-9]", "").cast("int"))

        df_gold = df_gold.withColumn("num_bedrooms", regexp_replace(col("specs_bedrooms_raw"), "[^0-9]", "").cast("int"))
        final_columns = [
            "url", "title", "district", "city",
            "price", "area_m2", "price_per_m2", "num_bedrooms",
            "house_direction", "has_legal_docs", "posted_date",
            "dt"
        ]

        df_final = df_gold.select(*final_columns) \
            .withColumn("gold_loaded_at", current_timestamp())
        jdbc_url = "jdbc:postgresql://db:5432/realestate_db"
        connection_properties = {
            "user" : "dev_user",
            "password" : "dev_password",
            "driver" : "org.postgresql.Driver"
        }

        print(f"Dang ghi du lieu vao")

        df_final.write.jdbc(
            url = jdbc_url,
            table = "fact_listings",
            mode="overwrite",
            properties = connection_properties
        )

        print("Da luu vao postgresql")
        print(f"Tong so ban ghi sliver:{df_sliver.count()}")
        print(f"Tong so ban ghi gold: {df_gold.count()}")
    
    except Exception as e:
        print(f"Loi khi xu ly etl:{e}")

    finally:
        spark.stop()

if __name__ == "__main__":
    main()