import streamlit as st


st.set_page_config(
    page_title="멀티페이지 앱",
    page_icon="🏠",
    layout="wide",
)

st.title("🏠 홈")
st.write("멀티페이지 Streamlit 앱에 오신 것을 환영합니다!")

st.markdown(
    """
## 페이지 목록

왼쪽 사이드바에서 페이지를 선택하세요.

1. **대시보드** - 주요 메트릭과 차트
2. **데이터 분석** - CSV 업로드 분석 도구
3. **설정** - 앱 환경 설정
"""
)

if "visits" not in st.session_state:
    st.session_state.visits = 0

st.session_state.visits += 1

col1, col2, col3 = st.columns(3)
col1.metric("총 사용자", "1,234", "+12%")
col2.metric("총 매출", "₩5,678,900", "+8%")
col3.metric("활성 세션", "42", "-3%")

st.info(f"현재 세션에서 홈이 열린 횟수: {st.session_state.visits}")
