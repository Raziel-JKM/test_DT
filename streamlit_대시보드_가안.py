#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
서울시 지하철 승하차 분석용 Streamlit 대시보드 가안

요구사항:
1) 데이터셋이 있는 디렉터리에서 바로 실행
2) H1~H5 가설을 추적할 수 있는 핵심 지표 탭 구성
3) 좌표 파일이 있으면 심야지수 지도까지 표시

실행:
streamlit run streamlit_대시보드_가안.py
"""

import pandas as pd
import streamlit as st
from pathlib import Path
from typing import List, Tuple

try:
    import altair as alt
except Exception:  # pragma: no cover
    alt = None

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

st.set_page_config(page_title="서울시 지하철 분석 대시보드", layout="wide")


def read_csv_fallback(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    return pd.read_csv(path)


def normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().replace("\ufeff", "") for c in df.columns]
    return df


def resolve_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    col_map = {str(c).strip().lower(): c for c in df.columns}
    for cand in candidates:
        key = str(cand).strip().lower()
        if key in col_map:
            return col_map[key]
    return None


def safe_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").fillna(0)


def route_count_from_raw(v: str) -> int:
    if pd.isna(v):
        return 0
    return len([x for x in str(v).split(",") if x.strip()])


def resolve_data_path(file_name: str) -> str:
    candidate = DATA_DIR / file_name
    if candidate.exists():
        return candidate.as_posix()
    return (BASE_DIR / file_name).as_posix()


@st.cache_data
def load_cleaned(path: str) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        return pd.DataFrame()

    df = read_csv_fallback(path)
    df = normalize_cols(df)
    if "job_ymd" in df.columns:
        df["job_ymd"] = df["job_ymd"].astype(str).str.strip()

    hour_on = [c for c in df.columns if c.endswith("_get_on_nope")]
    hour_off = [c for c in df.columns if c.endswith("_get_off_nope")]
    if not hour_on or not hour_off:
        return pd.DataFrame()

    for c in hour_on + hour_off:
        df[c] = safe_num(df[c])

    df["총승차"] = df[hour_on].sum(axis=1)
    df["총하차"] = df[hour_off].sum(axis=1)
    df["총유동량"] = df["총승차"] + df["총하차"]
    df["일자"] = pd.to_datetime(df["job_ymd"], format="%Y%m%d", errors="coerce")
    if "일자" in df.columns:
        df["월"] = df["일자"].dt.to_period("M").astype(str)
    df["AM_승차"] = df[[c for c in hour_on if c.split("_")[1] in {"7", "8", "9"}]].sum(axis=1)
    df["PM_승차"] = df[[c for c in hour_on if c.split("_")[1] in {"18", "19", "20"}]].sum(axis=1)
    df["AM_하차"] = df[[c for c in hour_off if c.split("_")[1] in {"7", "8", "9"}]].sum(axis=1)
    df["PM_하차"] = df[[c for c in hour_off if c.split("_")[1] in {"18", "19", "20"}]].sum(axis=1)
    df["심야수요0to5_승차"] = df[[c for c in hour_on if c.split("_")[1] in {"0", "1", "2", "3", "4", "5"}]].sum(axis=1)
    df["심야수요0to5_하차"] = df[[c for c in hour_off if c.split("_")[1] in {"0", "1", "2", "3", "4", "5"}]].sum(axis=1)
    return df


def aggregate_station_day(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    g = df.groupby(["job_ymd", "sttn", "일자"], as_index=False).agg(
        {
            "총승차": "sum",
            "총하차": "sum",
            "총유동량": "sum",
            "AM_승차": "sum",
            "PM_승차": "sum",
            "AM_하차": "sum",
            "PM_하차": "sum",
            "심야수요0to5_승차": "sum",
            "심야수요0to5_하차": "sum",
            "sbwy_rout_ln_nm": lambda x: ",".join(sorted(set(v for v in x.dropna().astype(str) if v))),
        }
    )
    g = g.copy()
    g["AM_승차점유"] = (g["AM_승차"] / g["총승차"]).replace([float("inf"), float("-inf")], 0).fillna(0)
    g["PM_승차점유"] = (g["PM_승차"] / g["총승차"]).replace([float("inf"), float("-inf")], 0).fillna(0)
    g["AM_하차점유"] = (g["AM_하차"] / g["총하차"]).replace([float("inf"), float("-inf")], 0).fillna(0)
    g["PM_하차점유"] = (g["PM_하차"] / g["총하차"]).replace([float("inf"), float("-inf")], 0).fillna(0)

    g["심야지수_승하차합"] = ((g["심야수요0to5_승차"] + g["심야수요0to5_하차"]) / g["총유동량"]).replace(
        [float("inf"), float("-inf")], 0
    ).fillna(0)
    am_den = (g["AM_승차"] + g["AM_하차"]).replace(0, pd.NA)
    pm_den = (g["PM_승차"] + g["PM_하차"]).replace(0, pd.NA)
    g["AM대칭"] = 1 - ((g["AM_승차"] - g["AM_하차"]).abs() / am_den)
    g["PM대칭"] = 1 - ((g["PM_승차"] - g["PM_하차"]).abs() / pm_den)
    g["AM대칭"] = pd.to_numeric(g["AM대칭"], errors="coerce").fillna(0.0)
    g["PM대칭"] = pd.to_numeric(g["PM대칭"], errors="coerce").fillna(0.0)

    g["노선수"] = g["sbwy_rout_ln_nm"].apply(route_count_from_raw)
    g["역군"] = g["노선수"].apply(
        lambda n: "환승역(3+선)" if n >= 3 else "경유/관문(2선)" if n == 2 else "일반역(1선)"
    )
    return g


def station_day_for_tracking(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    if df.empty:
        return df

    df_view = df.copy()
    if "job_ymd" in df_view.columns:
        df_view["job_ymd"] = df_view["job_ymd"].astype(str).str.strip()
    return df_view[(df_view["job_ymd"] >= start) & (df_view["job_ymd"] <= end)].copy()


def kpi_cards(values: List[Tuple[str, str, str]]):
    cols = st.columns(min(4, max(1, len(values))))
    for c, (l, v, d) in zip(cols, values):
        with c:
            st.metric(l, v, d if d else "")


def _is_altair_ready() -> bool:
    return alt is not None


def render_rainbow_line(df: pd.DataFrame, x_col: str, y_cols: list[str], height: int = 280):
    if df.empty or not y_cols:
        st.info("표시할 데이터가 없습니다.")
        return

    if not _is_altair_ready():
        st.line_chart(df.set_index(x_col)[y_cols])
        return

    plot_df = df[[x_col, *y_cols]].copy()
    for c in y_cols:
        plot_df[c] = pd.to_numeric(plot_df[c], errors="coerce")
    plot_df = plot_df.dropna(subset=y_cols, how="all")
    if plot_df.empty:
        st.info("표시할 데이터가 없습니다.")
        return

    parsed = pd.to_datetime(plot_df[x_col], errors="coerce")
    use_datetime = parsed.notna().sum() >= max(1, len(plot_df) * 0.5)
    if use_datetime:
        plot_df["x_plot"] = parsed
        x_enc = alt.X("x_plot:T", title=x_col, axis=alt.Axis(format="%Y%m%d", labelAngle=-45))
        x_tooltip = alt.Tooltip("x_plot:T", title=x_col, format="%Y-%m-%d")
        color_by_x = alt.Color("x_plot:T", scale=alt.Scale(scheme="rainbow"), legend=None)
    else:
        plot_df["x_plot"] = plot_df[x_col].astype(str)
        x_enc = alt.X("x_plot:N", title=x_col, axis=alt.Axis(labelAngle=-45))
        x_tooltip = alt.Tooltip("x_plot:N", title=x_col)
        color_by_x = alt.Color("x_plot:N", scale=alt.Scale(scheme="rainbow"), legend=None)

    long_df = (
        plot_df[["x_plot", *y_cols]]
        .melt(id_vars=["x_plot"], value_vars=y_cols, var_name="지표", value_name="값")
        .dropna(subset=["값"])
    )
    if long_df.empty:
        st.info("표시할 데이터가 없습니다.")
        return

    if len(y_cols) == 1:
        chart = (
            alt.Chart(long_df)
            .mark_line(point=True)
            .encode(
                x=x_enc,
                y=alt.Y("값:Q", title="값"),
                color=color_by_x,
                tooltip=[x_tooltip, alt.Tooltip("값:Q", format=".4f")],
            )
            .properties(height=height)
        )
    else:
        chart = (
            alt.Chart(long_df)
            .mark_line(point=True)
            .encode(
                x=x_enc,
                y=alt.Y("값:Q", title="값"),
                color=alt.Color("지표:N", scale=alt.Scale(scheme="rainbow"), legend=alt.Legend(title="지표")),
                tooltip=[x_tooltip, alt.Tooltip("지표:N"), alt.Tooltip("값:Q", format=".4f")],
            )
            .properties(height=height)
        )
    st.altair_chart(chart, use_container_width=True)


def render_rainbow_bar(df: pd.DataFrame, x_col: str, y_col: str, height: int = 280):
    if df.empty:
        st.info("표시할 데이터가 없습니다.")
        return

    if not _is_altair_ready():
        st.bar_chart(df.set_index(x_col)[y_col])
        return

    plot_df = df[[x_col, y_col]].copy()
    plot_df[y_col] = pd.to_numeric(plot_df[y_col], errors="coerce")
    plot_df = plot_df.dropna(subset=[y_col])
    if plot_df.empty:
        st.info("표시할 데이터가 없습니다.")
        return
    plot_df[x_col] = plot_df[x_col].astype(str)

    chart = (
        alt.Chart(plot_df)
        .mark_bar()
        .encode(
            x=alt.X(f"{x_col}:N", title=x_col, sort=None, axis=alt.Axis(labelAngle=-45)),
            y=alt.Y(f"{y_col}:Q", title=y_col),
            color=alt.Color(f"{x_col}:N", scale=alt.Scale(scheme="rainbow"), legend=None),
            tooltip=[alt.Tooltip(f"{x_col}:N", title=x_col), alt.Tooltip(f"{y_col}:Q", format=".4f")],
        )
        .properties(height=height)
    )
    st.altair_chart(chart, use_container_width=True)


def render_rainbow_bar_multi(df: pd.DataFrame, x_col: str, y_cols: list[str], height: int = 280):
    if df.empty or not y_cols:
        st.info("표시할 데이터가 없습니다.")
        return

    if not _is_altair_ready():
        st.bar_chart(df.set_index(x_col)[y_cols])
        return

    plot_df = df[[x_col, *y_cols]].copy()
    for c in y_cols:
        plot_df[c] = pd.to_numeric(plot_df[c], errors="coerce")
    long_df = (
        plot_df.melt(id_vars=[x_col], value_vars=y_cols, var_name="지표", value_name="값")
        .dropna(subset=["값"])
        .copy()
    )
    if long_df.empty:
        st.info("표시할 데이터가 없습니다.")
        return
    long_df[x_col] = long_df[x_col].astype(str)

    chart = (
        alt.Chart(long_df)
        .mark_bar()
        .encode(
            x=alt.X(f"{x_col}:N", title=x_col, sort=None, axis=alt.Axis(labelAngle=-45)),
            xOffset="지표:N",
            y=alt.Y("값:Q", title="값"),
            color=alt.Color("지표:N", scale=alt.Scale(scheme="rainbow"), legend=alt.Legend(title="지표")),
            tooltip=[alt.Tooltip(f"{x_col}:N", title=x_col), alt.Tooltip("지표:N"), alt.Tooltip("값:Q", format=".4f")],
        )
        .properties(height=height)
    )
    st.altair_chart(chart, use_container_width=True)


def render_rainbow_scatter(df: pd.DataFrame, x_col: str, y_col: str, color_col: str, size_col: str | None = None):
    if df.empty:
        st.info("표시할 데이터가 없습니다.")
        return

    if not _is_altair_ready():
        st.scatter_chart(df[[x_col, y_col]].set_index(x_col))
        return

    plot_df = df[[x_col, y_col, color_col] + ([size_col] if size_col else [])].copy()
    plot_df[x_col] = pd.to_numeric(plot_df[x_col], errors="coerce")
    plot_df[y_col] = pd.to_numeric(plot_df[y_col], errors="coerce")
    plot_df = plot_df.dropna(subset=[x_col, y_col])
    if plot_df.empty:
        st.info("표시할 데이터가 없습니다.")
        return
    if size_col is not None:
        plot_df[size_col] = pd.to_numeric(plot_df[size_col], errors="coerce").fillna(0)

    encode_kwargs = {
        "x": alt.X(f"{x_col}:Q", title=x_col),
        "y": alt.Y(f"{y_col}:Q", title=y_col),
        "color": alt.Color(
            f"{color_col}:N",
            scale=alt.Scale(scheme="rainbow"),
            legend=alt.Legend(title=color_col),
        ),
        "tooltip": [
            alt.Tooltip(f"{x_col}:Q", format=".4f"),
            alt.Tooltip(f"{y_col}:Q", format=".4f"),
            alt.Tooltip(f"{color_col}:N"),
        ],
    }
    if size_col is not None:
        encode_kwargs["size"] = alt.Size(
            f"{size_col}:Q",
            scale=alt.Scale(range=[20, 450]),
            legend=alt.Legend(title=size_col),
        )
    chart = alt.Chart(plot_df).mark_circle().encode(**encode_kwargs).properties(height=320)
    st.altair_chart(chart, use_container_width=True)


def section_h1(df_day: pd.DataFrame):
    st.subheader("H1. 피크(07~09, 18~20) 집중 추적")
    if df_day.empty:
        st.warning("H1 분석에 필요한 데이터가 비어있습니다.")
        return

    daily = df_day.groupby("job_ymd", as_index=False).agg(
        AM_승차_총=("AM_승차", "sum"),
        PM_승차_총=("PM_승차", "sum"),
        AM_하차_총=("AM_하차", "sum"),
        PM_하차_총=("PM_하차", "sum"),
        총승차=("총승차", "sum"),
        총하차=("총하차", "sum"),
    )

    total_on = daily["총승차"].sum()
    total_off = daily["총하차"].sum()
    m1 = daily["AM_승차_총"].sum() / max(total_on, 1)
    m2 = daily["PM_승차_총"].sum() / max(total_on, 1)
    m3 = daily["AM_하차_총"].sum() / max(total_off, 1)
    m4 = daily["PM_하차_총"].sum() / max(total_off, 1)

    kpi_cards(
        [
            ("AM 승차 비중", f"{m1:.2%}", "07~09"),
            ("PM 승차 비중", f"{m2:.2%}", "18~20"),
            ("AM 하차 비중", f"{m3:.2%}", "07~09"),
            ("PM 하차 비중", f"{m4:.2%}", "18~20"),
        ]
    )

    trend = daily.copy()
    trend["AM승차점유"] = pd.to_numeric(
        trend["AM_승차_총"] / trend["총승차"].replace(0, pd.NA), errors="coerce"
    ).fillna(0.0)
    trend["PM승차점유"] = pd.to_numeric(
        trend["PM_승차_총"] / trend["총승차"].replace(0, pd.NA), errors="coerce"
    ).fillna(0.0)
    trend["AM하차점유"] = pd.to_numeric(
        trend["AM_하차_총"] / trend["총하차"].replace(0, pd.NA), errors="coerce"
    ).fillna(0.0)
    trend["PM하차점유"] = pd.to_numeric(
        trend["PM_하차_총"] / trend["총하차"].replace(0, pd.NA), errors="coerce"
    ).fillna(0.0)

    render_rainbow_line(
        trend,
        "job_ymd",
        ["AM승차점유", "PM승차점유", "AM하차점유", "PM하차점유"],
        height=320,
    )

    station_rank = (
        df_day.groupby("sttn", as_index=False)
        .agg(AM승차점유=("AM_승차", "mean"), PM승차점유=("PM_승차", "mean"), 총유동량=("총유동량", "mean"))
        .sort_values("총유동량", ascending=False)
        .head(20)
    )
    station_rank["AM승차점유"] = station_rank["AM승차점유"].round(3)
    station_rank["PM승차점유"] = station_rank["PM승차점유"].round(3)
    c1, c2 = st.columns(2)
    with c1:
        render_rainbow_bar(station_rank, "sttn", "AM승차점유")
    with c2:
        render_rainbow_bar(station_rank, "sttn", "PM승차점유")

    st.dataframe(
        station_rank.rename(
            columns={"AM승차점유": "AM점유(평균)", "PM승차점유": "PM점유(평균)", "총유동량": "총유동량(평균)"}
        ),
        use_container_width=True,
    )


def section_h2(df_day: pd.DataFrame):
    st.subheader("H2. 경유/환승/관문 역 대칭성 추적")
    if df_day.empty:
        st.warning("H2 분석에 필요한 데이터가 비어있습니다.")
        return

    group = (
        df_day.groupby("역군")
        .agg(AM대칭_평균=("AM대칭", "mean"), PM대칭_평균=("PM대칭", "mean"), 표본수=("sttn", "nunique"))
        .reset_index()
    )
    st.dataframe(group, use_container_width=True)
    render_rainbow_bar_multi(group, "역군", ["AM대칭_평균", "PM대칭_평균"])

    st.markdown("### 역군별 대표역(대칭성 기준)")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### AM 대칭 높은 역")
        st.dataframe(
            df_day.sort_values("AM대칭", ascending=False).head(10)[
                ["sttn", "역군", "AM대칭", "PM대칭", "총승차"]
            ],
            use_container_width=True,
        )
    with c2:
        st.markdown("#### AM 대칭 낮은 역")
        st.dataframe(
            df_day.sort_values("AM대칭", ascending=True).head(10)[
                ["sttn", "역군", "AM대칭", "PM대칭", "총승차"]
            ],
            use_container_width=True,
        )

    scatter_data = df_day.groupby("sttn", as_index=False).agg(
        AM대칭=("AM대칭", "mean"), PM대칭=("PM대칭", "mean"), 총유동량=("총유동량", "mean"), 역군=("역군", "last")
    )
    render_rainbow_scatter(scatter_data, "AM대칭", "PM대칭", "역군", size_col="총유동량")


def section_h3(df_clean: pd.DataFrame):
    st.subheader("H3. 월별 계절성 및 이벤트성 변동")
    if df_clean.empty or "월" not in df_clean.columns:
        st.warning("월별 집계에 필요한 데이터가 비어있습니다.")
        return

    m = (
        df_clean.groupby("월", as_index=False)
        .agg(총유동량=("총유동량", "sum"), 날짜=("일자", "min"))
        .sort_values("월")
    )
    m["총유동량"] = safe_num(m["총유동량"])
    m["추세(12M)"] = m["총유동량"].rolling(12, min_periods=6).mean()
    m["계절성_잔차"] = m["총유동량"] - m["추세(12M)"]
    m["잔차"] = m["계절성_잔차"] - m["계절성_잔차"].rolling(12, min_periods=6).mean()

    render_rainbow_line(m, "월", ["총유동량", "추세(12M)"])
    render_rainbow_line(m, "월", ["계절성_잔차"], height=220)

    z = m.copy()
    sigma = z["잔차"].std(ddof=0)
    if sigma == 0 or pd.isna(sigma):
        z["이상치"] = False
    else:
        z["zscore"] = z["잔차"] / sigma
        z["이상치"] = z["zscore"].abs() >= 2
    st.markdown("### 월별 이상치 후보")
    st.dataframe(z[z["이상치"]][["월", "총유동량", "잔차", "zscore"]].head(20), use_container_width=True)


def section_h4():
    st.subheader("H4. 심야 수요(0~5시) 추적")
    st.markdown("데이터 파일: `가설4_역별_심야지수.csv`, `가설4_노선별_심야지수.csv`")

    st_file_station = Path(resolve_data_path("가설4_역별_심야지수.csv"))
    st_file_line = Path(resolve_data_path("가설4_노선별_심야지수.csv"))
    if not st_file_station.exists() or not st_file_line.exists():
        st.info("심야 수요 산출 파일을 찾을 수 없습니다.")
        return

    stn = normalize_cols(read_csv_fallback(st_file_station))
    line = normalize_cols(read_csv_fallback(st_file_line))
    line_name_col = resolve_column(line, ["노선", "sbwy_rout_ln_nm", "노선명", "line_name", "line"])
    stn_name_col = resolve_column(stn, ["역명", "sttn", "역", "station_name", "station"])
    if stn_name_col is None:
        st.warning("역별 심야지수 파일에서 역명 컬럼을 찾을 수 없습니다.")
        return

    stn["심야지수"] = safe_num(stn.get("심야지수", 0))
    stn["심야수요_0to5"] = safe_num(stn.get("심야수요_0to5", 0))
    n = st.slider("역 별 TOP", 10, 100, 20, 10)

    c1, c2 = st.columns(2)
    with c1:
        render_rainbow_bar(
            stn.sort_values("심야지수", ascending=False).head(n),
            stn_name_col,
            "심야지수",
        )
    with c2:
        render_rainbow_bar(
            stn.sort_values("심야수요_0to5", ascending=False).head(n),
            stn_name_col,
            "심야수요_0to5",
        )

    st.dataframe(stn.sort_values("심야수요_0to5", ascending=False).head(20), use_container_width=True)

    if line_name_col and "심야지수" in line.columns:
        render_rainbow_bar(line, line_name_col, "심야지수")
    else:
        st.info("노선별 심야지수 컬럼명을 확인해 주세요. 필요 컬럼: 노선(또는 노선명), 심야지수")

    # 지도(좌표 파일이 있으면)
    coord_path = DATA_DIR / "station_coords.csv"
    if not coord_path.exists():
        coord_path = BASE_DIR / "station_coords.csv"
    if coord_path.exists():
        coord = normalize_cols(read_csv_fallback(coord_path))
        lat_col = next((c for c in coord.columns if c in ["lat", "latitude", "위도", "y", "Y"]), None)
        lon_col = next((c for c in coord.columns if c in ["lon", "lng", "longitude", "경도", "x", "X"]), None)
        coord_name_col = resolve_column(
            coord, ["역명", "sttn", "역", "station_name", "station", stn_name_col or ""]
        )
        if lat_col and lon_col and coord_name_col:
            merged = stn.merge(coord, left_on=stn_name_col, right_on=coord_name_col, how="left")
            merged = merged.rename(columns={lat_col: "lat", lon_col: "lon"})
            merged = merged[[c for c in [coord_name_col, "lat", "lon", "심야지수"] if c in merged.columns]].dropna()
            if not merged.empty:
                st.map(merged.rename(columns={coord_name_col: "역명"}), size=20, zoom=10)
        else:
            st.info("좌표 컬럼명을 `lat`/`lon` 또는 `위도`/`경도`로 맞춰주세요.")
    else:
        st.caption("심야 지도 표시를 원하면 `station_coords.csv`(역명, 위도, 경도 또는 lon/lon) 추가.")


def section_h5():
    st.subheader("H5. 중복 병합 정책 민감도 추적")
    f_day = Path(resolve_data_path("가설5_일일총량_정책비교.csv"))
    f_line = Path(resolve_data_path("가설5_노선별총량_정책비교.csv"))
    f_origin = Path(resolve_data_path("가설5_원본_일일총량_정책비교.csv"))

    if not all(p.exists() for p in [f_day, f_line]):
        st.warning("정책 비교 파일을 찾을 수 없습니다.")
        return

    day = normalize_cols(read_csv_fallback(f_day))
    line = normalize_cols(read_csv_fallback(f_line))

    for c in ["raw_total", "max_total", "first_total", "max_delta_abs", "first_delta_abs"]:
        if c in day.columns:
            day[c] = safe_num(day[c])
    for c in ["raw_total", "max_total", "first_total", "max_delta_abs", "first_delta_abs"]:
        if c in line.columns:
            line[c] = safe_num(line[c])

    total = pd.DataFrame(
        {
            "지표": ["raw_total", "max_total", "first_total"],
            "값": [day["raw_total"].sum(), day["max_total"].sum(), day["first_total"].sum()],
        }
    )
    st.dataframe(total, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 노선별 손실량")
        line_name_col = resolve_column(line, ["sbwy_rout_ln_nm", "노선", "line_name", "line", "노선명"])
        if "max_delta_abs" in line.columns and "first_delta_abs" in line.columns:
            top_line = line.sort_values("max_delta_abs", key=lambda s: s.abs(), ascending=False).head(30)
            if line_name_col is not None:
                render_rainbow_bar_multi(top_line, line_name_col, ["max_delta_abs", "first_delta_abs"], height=320)
            else:
                st.info("노선별 손실량 차트를 그리기 위한 노선명 컬럼이 필요합니다.")
    with c2:
        st.markdown("### 일별 손실량(Top)")
        top_day = day.sort_values("max_delta_abs", key=lambda s: s.abs(), ascending=False).head(20)
        st.dataframe(top_day, use_container_width=True)

    if f_origin.exists():
        origin = normalize_cols(read_csv_fallback(f_origin))
        if "sum_loss_abs" in origin.columns:
            origin["sum_loss_abs"] = safe_num(origin["sum_loss_abs"])
            st.caption("원본 기준 max 정책 손실 합: " + f"{origin['sum_loss_abs'].sum():,.0f}")


def overview(df_clean: pd.DataFrame, df_station_day: pd.DataFrame):
    st.title("서울시 지하철 시간대별 승하차 분석 대시보드")
    st.write("가설 기반 지표 추적용 가안(1안)")

    if df_clean.empty:
        st.error("기본 정제 파일을 찾지 못했습니다. 사이드바에서 파일 경로를 확인하세요.")
        st.stop()

    latest = df_clean["job_ymd"].astype(str).max()
    earliest = df_clean["job_ymd"].astype(str).min()
    total_rows = len(df_clean)
    stations = df_clean["sttn"].nunique()
    lines = df_clean["sbwy_rout_ln_nm"].nunique()
    total_flow = df_clean["총유동량"].sum()
    kpi_cards(
        [
            ("분석 기간", f"{earliest} ~ {latest}", None),
            ("행 수", f"{total_rows:,}", "역-일-노선"),
            ("역 수", f"{stations:,}", "고유 역"),
            ("노선 수", f"{lines}", "고유 노선"),
            ("총유동량", f"{total_flow:,.0f}", "승+하합"),
        ]
    )

    daily_total = (
        df_station_day.groupby("job_ymd", as_index=False).agg(총유동량=("총유동량", "sum")).sort_values("job_ymd").reset_index(drop=True)
    )
    daily_total["7일_이동평균"] = daily_total["총유동량"].rolling(7, min_periods=3).mean()
    render_rainbow_line(daily_total, "job_ymd", ["총유동량", "7일_이동평균"], height=320)


def main():
    st.sidebar.title("데이터 입력")
    cleaned_default = resolve_data_path("서울시 지하철 호선별 역별 시간대별 승하차 인원 정보_클랜징_최종.csv")
    cleaned_path = st.sidebar.text_input("정제본 CSV", cleaned_default)

    df_clean = load_cleaned(cleaned_path)
    df_station_day = aggregate_station_day(df_clean)
    if df_station_day.empty:
        st.warning("데이터 정합성 이슈: 집계 결과가 없습니다. 파일 형식과 컬럼명을 확인하세요.")
        return

    st.sidebar.markdown("---")
    unique_dates = sorted(df_station_day["job_ymd"].dropna().astype(str).unique())
    min_d = unique_dates[0]
    max_d = unique_dates[-1]
    start, end = st.sidebar.select_slider(
        "일자 범위",
        options=unique_dates,
        value=(min_d, max_d),
    )

    target = station_day_for_tracking(df_station_day, start, end)

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["개요", "H1", "H2", "H3", "H4", "H5"])
    with tab1:
        overview(df_clean, target)
    with tab2:
        section_h1(target)
    with tab3:
        section_h2(target)
    with tab4:
        section_h3(df_clean)
    with tab5:
        section_h4()
    with tab6:
        section_h5()


if __name__ == "__main__":
    main()
