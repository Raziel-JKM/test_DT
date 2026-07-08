import streamlit as st


st.set_page_config(page_title="설정", page_icon="⚙️", layout="wide")

st.title("⚙️ 설정")

if "settings" not in st.session_state:
    st.session_state.settings = {
        "theme": "Light",
        "language": "한국어",
        "notifications": True,
        "auto_refresh": False,
    }

st.subheader("일반 설정")

theme = st.radio(
    "테마",
    ["Light", "Dark"],
    index=0 if st.session_state.settings["theme"] == "Light" else 1,
)
st.session_state.settings["theme"] = theme

language_options = ["한국어", "English", "日本語"]
language = st.selectbox(
    "언어",
    language_options,
    index=language_options.index(st.session_state.settings["language"]),
)
st.session_state.settings["language"] = language

st.divider()

st.subheader("알림 설정")

notifications = st.checkbox(
    "푸시 알림 받기",
    value=st.session_state.settings["notifications"],
)
st.session_state.settings["notifications"] = notifications

auto_refresh = st.checkbox(
    "자동 새로고침",
    value=st.session_state.settings["auto_refresh"],
)
st.session_state.settings["auto_refresh"] = auto_refresh

if auto_refresh:
    st.slider("새로고침 간격 (초)", 5, 60, 30)

st.divider()

if st.button("설정 저장"):
    st.success("설정이 저장되었습니다!")

with st.expander("현재 설정 보기"):
    st.json(st.session_state.settings)
