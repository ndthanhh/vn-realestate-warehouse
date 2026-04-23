from pyspark.sql import SparkSession
from pyspark.sql.functions import col, regexp_replace, to_date, lit, trim, split

def safe_struct_col(df, struct_col_name, sub_col_name):
    try:
        struct_schema=df.schema[struct_col_name].dataType
        existing_fields = [f.name for f in struct_schema.fields]
        if sub_col_name in existing_fields:
            return col(f"{struct_col_name}.`{sub_col_name}`")
    except Exception:
        pass
    return lit(None).cast("string")

def create_spark_session():
    return SparkSession.builder\
        .appName("ETL_Bronze_to_Sliver_BatDongSan")\
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000")\
        .config("spark.hadoop.fs.s3a.access.key", "minioadmin")\
        .config("spark.hadoop.fs.s3a.secret.key", "minioadmin")\
        .config("spark.hadoop.fs.s3a.path.style.access", "true")\
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")\
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled","false")\
        .getOrCreate()

def main():
    spark = create_spark_session()

    bronze_path = "s3a://realestate/bronze/batdongsan/*/*.json"
    try:
        df_bronze = spark.read.json(bronze_path)
    except Exception as e:
        print(f"Loi tai len: {e}")
        spark.stop()
        return

    try:
        df_sliver = df_bronze.select(
            col("url"),
            col("title"),
            col("address"),
            col("address_line_2"),
            col("description"),
            col("crawled_at").cast("timestamp"),

            safe_struct_col(df_bronze, "short_info", "Khoảng giá").alias("price_raw"),
            safe_struct_col(df_bronze, "short_info", "Khoảng giá(ext)").alias("price_per_m2_raw"),
            safe_struct_col(df_bronze, "short_info", "Diện tích").alias("area_raw"),
            safe_struct_col(df_bronze, "short_info", "Phòng ngủ").alias("bedrooms_raw"),
            safe_struct_col(df_bronze, "short_info", "Ngày đăng").alias("posted_date_str"),
            safe_struct_col(df_bronze, "short_info", "Ngày hết hạn").alias("expired_date_str"),

            safe_struct_col(df_bronze, "specs", "Số phòng ngủ").alias("specs_bedrooms_raw"),
            safe_struct_col(df_bronze, "specs", "Hướng nhà").alias("house_direction"),
            safe_struct_col(df_bronze, "specs", "Pháp lý").alias("legal_status")
        )

        addr_split = split(col("address_line_2"), ",")
        df_sliver  = df_sliver.withColumn("district", trim(addr_split.getItem(0)))\
            .withColumn("city", trim(addr_split.getItem(1)))
        
        # Làm sạch district và cityLabels
        df_sliver = df_sliver.withColumn("district", regexp_replace("district", "^(Quận|Huyện|Thị xã)\\s+", ""))\
            .withColumn("city", regexp_replace("city", "\\s+cũ$", ""))
        
        df_sliver = df_sliver.withColumn("price", regexp_replace("price_raw", "[^0-9,]", "")) \
             .withColumn("price", regexp_replace("price", ",", ".").cast("double"))

        df_sliver = df_sliver.withColumn("area_m2", regexp_replace("area_raw", "[^0-9,]", ""))\
            .withColumn("area_m2", regexp_replace("area_m2", ",", ".").cast("double"))

        df_sliver = df_sliver.withColumn("price_per_m2", regexp_replace("price_per_m2_raw", "[^0-9,]", ""))\
            .withColumn("price_per_m2", regexp_replace("price_per_m2", ",", ".").cast("double"))

        df_sliver = df_sliver.withColumn("posted_date", to_date("posted_date_str", "dd/MM/yyyy"))
        df_sliver = df_sliver.withColumn("dt", to_date(col("crawled_at")))

    except Exception as e:
        print(f"Loi khi xu ly: {e}")
        df_sliver = df_bronze

    sliver_path = "s3a://realestate/silver/batdongsan/"
    df_sliver.write.mode("overwrite").partitionBy("dt").parquet(sliver_path)
    print(f"Da luu du lieu tai: {sliver_path}")
    spark.stop()

if __name__ == "__main__":
    main()