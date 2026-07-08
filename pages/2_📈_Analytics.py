import numpy as np
import pandas as pd
import streamlit as st


st.set_page_config(page_title="데이터 분석", page_icon="📈", layout="wide")

st.title("📈 데이터 분석")

uploaded_file = st.file_uploader("CSV 파일을 업로드하세요", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    st.subheader("데이터 미리보기")
    st.dataframe(df.head(), use_container_width=True)

    st.subheader("기본 통계")
    st.write(df.describe(include="all"))

    numeric_columns = df.select_dtypes(include=[np.number]).columns
    if len(numeric_columns) > 0:
        selected_col = st.selectbox("분석할 컬럼 선택", numeric_columns)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("평균", f"{df[selected_col].mean():.2f}")
            st.metric("중앙값", f"{df[selected_col].median():.2f}")

        with col2:
            st.metric("최댓값", f"{df[selected_col].max():.2f}")
            st.metric("최솟값", f"{df[selected_col].min():.2f}")

        st.line_chart(df[selected_col])
    else:
        st.warning("숫자형 컬럼이 없습니다.")
else:
    st.info("CSV 파일을 업로드하여 분석을 시작하세요.")
