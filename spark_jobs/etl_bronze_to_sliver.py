from pyspark.sql import SparkSession
from pyspark.sql.functions import col, regexp_replace, to_date, lit, trim, split, element_at, when, size
import os
from dotenv import load_dotenv

load_dotenv()

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
        .config("spark.hadoop.fs.s3a.endpoint", f"http://{os.getenv('MINIO_ENDPOINT', 'minio:9000')}")\
        .config("spark.hadoop.fs.s3a.access.key", os.getenv("MINIO_ROOT_USER", "minioadmin"))\
        .config("spark.hadoop.fs.s3a.secret.key", os.getenv("MINIO_ROOT_PASSWORD", "minioadmin"))\
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

        # LỌC RÁC: Chỉ giữ lại những tin có Data hợp lệ (bị Cloudflare chặn sẽ mất title)
        df_sliver = df_sliver.filter(col("title").isNotNull() & (trim(col("title")) != ""))

        addr2_arr = split(col("address_line_2"), ",")
        
        # LỌC RÁC: Loại bỏ các dòng không có address_line_2 hợp lệ (phải có ít nhất 2 thành phần)
        # Vì address_line_1 là địa chỉ sau sáp nhập nên không đồng nhất.
        df_sliver = df_sliver.filter(size(addr2_arr) >= 2)

        # Lấy district và city trực tiếp từ address_line_2
        df_sliver = df_sliver.withColumn("district", trim(element_at(addr2_arr, 1)))
        df_sliver = df_sliver.withColumn("city", trim(element_at(addr2_arr, 2)))
        
        # Làm sạch: Bỏ chữ Quận/Huyện ở quận (để lại Phường/Xã), bỏ chữ 'mới'/'cũ' ở Tỉnh
        df_sliver = df_sliver.withColumn("district", regexp_replace("district", "^(Quận|Huyện|Thị xã)\\s+", ""))\
            .withColumn("city", regexp_replace("city", "\\s+(mới|cũ)$", ""))
            
        # CHỈ GIỮ LẠI XÃ/PHƯỜNG: Xóa toàn bộ các dòng không có chữ Xã hoặc Phường ở trước (đây là các giá trị cũ hoặc lấy sai tuyến)
        df_sliver = df_sliver.filter(col("district").rlike("^(Xã|Phường)\\s"))
        
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
        spark.stop()
        raise  # DỪNG NGAY, không ghi đè Silver bằng dữ liệu Bronze thô

    sliver_path = "s3a://realestate/silver/batdongsan/"
    df_sliver.write.mode("overwrite").partitionBy("dt").parquet(sliver_path)
    print(f"Da luu du lieu tai: {sliver_path}")
    spark.stop()

if __name__ == "__main__":
    main()