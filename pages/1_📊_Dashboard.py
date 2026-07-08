import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st


st.set_page_config(page_title="대시보드", page_icon="📊", layout="wide")

st.title("📊 대시보드")


@st.cache_data
def load_data():
    dates = pd.date_range("2024-01-01", periods=30)
    return pd.DataFrame(
        {
            "날짜": dates,
            "매출": np.random.randint(100, 500, 30),
            "방문자": np.random.randint(50, 200, 30),
        }
    )


df = load_data()

st.sidebar.header("필터")
date_range = st.sidebar.date_input(
    "날짜 범위",
    value=(df["날짜"].min().date(), df["날짜"].max().date()),
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
    mask = (df["날짜"].dt.date >= start_date) & (df["날짜"].dt.date <= end_date)
    filtered_df = df.loc[mask]
else:
    filtered_df = df

col1, col2 = st.columns(2)

with col1:
    st.subheader("매출 추이")
    fig = px.line(filtered_df, x="날짜", y="매출")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("방문자 수")
    fig = px.bar(filtered_df, x="날짜", y="방문자")
    st.plotly_chart(fig, use_container_width=True)

with st.expander("원본 데이터 보기"):
    st.dataframe(filtered_df, use_container_width=True)
