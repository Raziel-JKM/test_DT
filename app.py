"""Streamlit entrypoint for cloud deployment."""

from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parent
APP_SRC = ROOT / "streamlit_대시보드_가안.py"

if not APP_SRC.exists():
    raise FileNotFoundError(f"앱 소스 파일을 찾을 수 없습니다: {APP_SRC}")

# Cloud runner executes this file directly.
runpy.run_path(APP_SRC, run_name="__main__")
