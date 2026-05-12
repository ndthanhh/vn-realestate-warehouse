import streamlit as st
import pandas as pd
import psycopg2 
import plotly.express as px
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title = "VN Realestate Dashboard",
    page_icon = "🏠",
    layout = "wide",
)

@st.cache_resource
def get_connection():
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5439")
    database = os.getenv("POSTGRES_DB", "realestate_db")
    user = os.getenv("POSTGRES_USER", "dev_user")
    password = os.getenv("POSTGRES_PASSWORD", "dev_password")
    
    return psycopg2.connect(
        host = host,
        port = port,
        database = database,
        user = user,
        password = password
    )

@st.cache_data(ttl=600)
def load_data():
    conn = get_connection()
    query = "SELECT * FROM fact_listings"
    df = pd.read_sql(query, conn)
    return df

df = load_data()

df['price'] = pd.to_numeric(df['price'], errors = 'coerce')
df['area_m2'] = pd.to_numeric(df['area_m2'], errors = 'coerce')

st.title("🏠 Dashboard Thị trường Chung cư Việt Nam")
total_rows =  len(df)
last_updated = df['gold_loaded_at'].max() if total_rows > 0 else "Unknown"
st.markdown(f"**Tổng số tin đăng:** {total_rows} | **Cập nhật lúc:** {last_updated}")

if total_rows == 0:
    st.warning("Dữ liệu trong Database đang trống.")
    st.stop()

st.sidebar.header("🔍 Bộ lọc Phân Tích")

cities = sorted(df['city'].dropna().unique().tolist())
selected_city = st.sidebar.selectbox("Chọn thành phố", ["Tất cả"]+cities)

filtered_df = df.copy()
if selected_city != "Tất cả":
    filtered_df = filtered_df[filtered_df['city'] == selected_city]

if len(filtered_df) == 0:
    st.warning("Không có dữ liệu cho bộ lọc này!")
    st.stop()

min_price = float(filtered_df['price'].min())
max_price = float(filtered_df['price'].max())
if min_price == max_price:
    price_range = (min_price, max_price)
else:
    price_range = st.sidebar.slider("Khoảng giá (tỷ VNĐ)", min_price, max_price, (min_price, max_price))

min_price_m2 = float(filtered_df['price_per_m2'].min())
max_price_m2 = float(filtered_df['price_per_m2'].max())
if min_price_m2 == max_price_m2:
    price_m2_range = (min_price_m2, max_price_m2)
else:
    price_m2_range = st.sidebar.slider("Khoảng giá trên m2 (triệu/m2)", min_price_m2, max_price_m2, (min_price_m2, max_price_m2))

bedrooms = st.sidebar.multiselect("Số phòng ngủ", sorted(filtered_df['num_bedrooms'].dropna().unique()))

filtered_df = filtered_df[
    (filtered_df['price'] >= price_range[0]) & 
    (filtered_df['price'] <= price_range[1]) &
    (filtered_df['price_per_m2'] >= price_m2_range[0]) &
    (filtered_df['price_per_m2'] <= price_m2_range[1])
]
if bedrooms:
    filtered_df = filtered_df[filtered_df['num_bedrooms'].isin(bedrooms)]

col11, col12, col13, col14 = st.columns(4)
col11.metric("Lượng tin hiển thị: ", len(filtered_df))
col12.metric("Giá trung bình: ", f"{filtered_df['price'].mean():.2f} tỷ")
col13.metric("Diện tích TB: ", f"{filtered_df['area_m2'].mean():.2f} m2")
col14.metric("Có sổ: ", f"{int(filtered_df['has_legal_docs'].sum())}")

st.divider()

colA, colB = st.columns(2)

with colA:
    st.subheader("📊 Giá trung bình theo Xã/Phường")
    avg_price = filtered_df.groupby('district')['price'].mean().sort_values(ascending=False).head(15).reset_index()
    if not avg_price.empty:
        fig1 = px.bar(avg_price, x='district', y='price',
                     labels={'district':'Xã/Phường', 'price':'Giá trị trung bình'},
                     color='price', color_continuous_scale='RdYlGn_r')
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.write("Không đủ dữ liệu")

with colB:
    st.subheader("⚖️ Tương quan Diện tích - Tổng giá")
    if not filtered_df.empty:
        # Sửa lại cho dễ nhìn theo yêu cầu của bạn
        fig2 = px.scatter(filtered_df, x='area_m2', y='price', 
                         color='city', hover_data=['title', 'district', 'price_per_m2'], 
                         labels={'area_m2':'Diện tích (m²)', 'price': 'Tổng giá (tỷ)', 'city': 'Thành phố'}, 
                         opacity=0.8) # Tăng opacity
        fig2.update_traces(marker=dict(size=10)) # Điểm to hơn chút cho dễ nhìn
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.write("Không đủ dữ liệu")

st.divider()
# VẼ THÊM biểu đồ đơn giá m2 ở hàng dưới
st.subheader("💰 Phân tích Đơn giá trên m² theo Khu vực")
avg_price_m2 = filtered_df.groupby('district')['price_per_m2'].mean().sort_values(ascending=False).head(15).reset_index()
if not avg_price_m2.empty:
    fig_m2 = px.bar(avg_price_m2, x='district', y='price_per_m2',
                   labels={'district':'Xã/Phường', 'price_per_m2':'Giá TB (Triệu/m²)'},
                   color='price_per_m2', color_continuous_scale='Viridis')
    st.plotly_chart(fig_m2, use_container_width=True)
else:
    st.write("Không đủ dữ liệu")

colC, colD = st.columns(2)

with colC:
    st.subheader("Tỉ lệ có sổ")
    has_docs = int(filtered_df['has_legal_docs'].sum())
    no_docs = len(filtered_df) - has_docs
    fig3 = px.pie(values=[has_docs, no_docs], 
                  names=['Có Sổ / Pháp lý an toàn', 'Không rõ / Đang chờ'],
                  color_discrete_sequence=['#2ecc71', '#e74c3c'])
    st.plotly_chart(fig3, use_container_width=True)

with colD:
    if selected_city == "Tất cả":
        st.subheader("📊 Mức độ phân bố giá giữa các tỉnh")
        fig4 = px.box(filtered_df, x='city', y='price', color='city',
                    labels={'city': 'Thành phố', 'price': 'Giá (tỷ VNĐ)'})
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.subheader(f"📊 Mức độ phân bố giá tại {selected_city}")
        fig4 = px.histogram(filtered_df, x='price', nbins=20,
                            labels={'price': 'Khoảng giá (tỷ VNĐ)'},
                            color_discrete_sequence=['indigo'])
        st.plotly_chart(fig4, use_container_width=True)

st.divider()
st.subheader("📋 Bảng tra cứu trực tiếp")
st.dataframe(filtered_df[['title', 'city', 'district', 'price', 'area_m2', 'num_bedrooms', 'url']], use_container_width=True, hide_index=True)