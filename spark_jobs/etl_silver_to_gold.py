from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp, regexp_replace, lower, when, split, trim
import os
from dotenv import load_dotenv

load_dotenv()

def create_spark_session():
    return SparkSession.builder\
        .appName("ETL_Silver_to_Gold")\
        .config("spark.hadoop.fs.s3a.endpoint", f"http://{os.getenv('MINIO_ENDPOINT', 'minio:9000')}")\
        .config("spark.hadoop.fs.s3a.access.key", os.getenv("MINIO_ROOT_USER", "minioadmin"))\
        .config("spark.hadoop.fs.s3a.secret.key", os.getenv("MINIO_ROOT_PASSWORD", "minioadmin"))\
        .config("spark.hadoop.fs.s3a.path.style.access", "true")\
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")\
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")\
        .getOrCreate()

def main():
    spark = create_spark_session()

    sliver_path = "s3a://realestate/silver/batdongsan/"
    db_host = os.getenv("DB_HOST", "db")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB", "realestate_db")
    db_user = os.getenv("POSTGRES_USER", "dev_user")
    db_pass = os.getenv("POSTGRES_PASSWORD", "dev_password")

    jdbc_url = f"jdbc:postgresql://{db_host}:{db_port}/{db_name}"
    connection_properties = {
        "user" : db_user,
        "password" : db_pass,
        "driver" : "org.postgresql.Driver"
    }

    try: 
        print(f"Dang doc du lieu tu: {sliver_path}")
        df_sliver = spark.read.parquet(sliver_path)

        print("Dang khu trung lap va lam sach du lieu...")
        df_gold = df_sliver.dropDuplicates(["url"])
        df_gold = df_gold.withColumn("has_legal_docs", 
            when(lower(col("legal_status")).contains("sổ") | 
                 lower(col("legal_status")).contains("đỏ") | 
                 lower(col("legal_status")).contains("hồng"), 1)
            .otherwise(0))
        df_gold = df_gold.withColumn("num_bedrooms", 
            regexp_replace(col("specs_bedrooms_raw"), "[^0-9]", "").cast("int"))

        # Trích xuất tên dự án thông minh:
        # 1. Tách địa chỉ thành mảng
        # 2. Loại bỏ các phần tử bắt đầu bằng "Số" hoặc chỉ chứa số/mã nhà (ví dụ: 54, 233B)
        # 3. Lấy phần tử đầu tiên còn lại làm tên dự án
        addr_parts = split(col("address"), ",")
        

        
        from pyspark.sql.functions import expr
        df_gold = df_gold.withColumn("addr_array", addr_parts)
        df_gold = df_gold.withColumn("project_name", expr("filter(addr_array, x -> NOT (trim(x) rlike '^[0-9/\\\\sA-Za-z]{1,6}$' OR lower(trim(x)) LIKE 'số%'))[0]"))
        df_gold = df_gold.withColumn("project_name", trim(col("project_name")))

        final_columns = [
            "url", "project_name", "title", "district", "city",
            "price", "area_m2", "price_per_m2", "num_bedrooms",
            "house_direction", "has_legal_docs", "posted_date",
            "dt"
        ]

        df_final = df_gold.select(*final_columns) \
            .withColumn("gold_loaded_at", current_timestamp())

        # === UPSERT: Ghi vào bảng tạm rồi gộp vào bảng chính ===
        # Bước 1: Ghi dữ liệu mới vào bảng staging (ghi đè staging là OK)
        print("Dang ghi du lieu vao bang staging...")
        df_final.write.jdbc(
            url=jdbc_url,
            table="stg_listings",
            mode="overwrite",
            properties=connection_properties
        )

        # Bước 2: Chạy SQL UPSERT từ staging → fact_listings
        print("Dang upsert vao bang fact_listings...")
        # Đăng ký Driver qua Spark context để tránh lỗi ClassNotFound
        spark._jvm.org.apache.spark.sql.execution.datasources.jdbc.DriverRegistry.register("org.postgresql.Driver")
        conn = spark._jvm.java.sql.DriverManager.getConnection(
            jdbc_url, db_user, db_pass
        )
        stmt = conn.createStatement()

        upsert_sql = """
            INSERT INTO fact_listings 
                (url, project_name, title, district, city, price, area_m2, price_per_m2,
                 num_bedrooms, house_direction, has_legal_docs, posted_date, dt, gold_loaded_at)
            SELECT url, project_name, title, district, city, price, area_m2, price_per_m2,
                   num_bedrooms, house_direction, has_legal_docs, posted_date, dt, gold_loaded_at
            FROM stg_listings
            ON CONFLICT (url) DO UPDATE SET
                project_name = EXCLUDED.project_name,
                title = EXCLUDED.title,
                district = EXCLUDED.district,
                city = EXCLUDED.city,
                price = EXCLUDED.price,
                area_m2 = EXCLUDED.area_m2,
                price_per_m2 = EXCLUDED.price_per_m2,
                num_bedrooms = EXCLUDED.num_bedrooms,
                house_direction = EXCLUDED.house_direction,
                has_legal_docs = EXCLUDED.has_legal_docs,
                posted_date = EXCLUDED.posted_date,
                dt = EXCLUDED.dt,
                gold_loaded_at = EXCLUDED.gold_loaded_at;
        """
        stmt.executeUpdate(upsert_sql)
        stmt.executeUpdate("DROP TABLE IF EXISTS stg_listings")
        stmt.close()
        conn.close()

        print("=" * 50)
        print(" THANH CONG: UPSERT HOAN TAT ")
        print(f" Tong so ban ghi Silver: {df_sliver.count()}")
        print(f" Tong so ban ghi Gold (sau khu trung): {df_final.count()}")
        print("=" * 50)
    
    except Exception as e:
        print(f"Loi khi xu ly etl: {e}")

    finally:
        spark.stop()

if __name__ == "__main__":
    main()