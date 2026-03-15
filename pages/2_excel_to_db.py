"""엑셀 → DB 일괄 Import 페이지"""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from db.connection import import_risk_codes_to_db, test_connection

st.set_page_config(page_title="엑셀 → DB Import", layout="wide")

st.title("엑셀 → DB 일괄 Import")
st.caption("엑셀 파일 업로드 또는 복사·붙여넣기로 데이터를 가져와 DB에 반영할 수 있습니다.")

# DB 연결 확인
ok, msg = test_connection()
if not ok:
    st.error(f"DB 연결 실패: {msg}")
    st.info("storage/risk_code.db (SQLite)를 사용합니다. DB 초기화: python -m scripts.init_db")
    st.stop()

st.success(f"DB 연결: {msg}")

st.divider()

input_mode = st.radio(
    "데이터 입력 방식",
    ["텍스트 붙여넣기 (엑셀에서 복사)", "엑셀 파일 업로드"],
    index=0,
    horizontal=True,
)

df_raw = None

if input_mode == "텍스트 붙여넣기 (엑셀에서 복사)":
    st.markdown("""
    **엑셀에서 CODE, NM 컬럼(또는 해당 데이터)을 선택한 뒤 Ctrl+C로 복사하고 아래에 붙여넣으세요.**  
    - 첫 줄이 헤더(컬럼명)인 경우 자동 인식됩니다.  
    - 탭 또는 쉼표로 구분된 텍스트를 지원합니다.
    """)
    has_header = st.checkbox("첫 줄이 헤더(컬럼명)입니다", value=True, key="has_header")
    pasted_text = st.text_area(
        "데이터 붙여넣기",
        placeholder="예시:\nCODE\tNM\nK001\t코드이름1\nK002\t코드이름2\n\n또는\nCODE,NM\nK001,코드이름1\nK002,코드이름2",
        height=200,
        key="pasted_csv",
    )
    if not pasted_text.strip():
        st.info("엑셀에서 복사한 데이터를 위 입력창에 붙여넣어 주세요.")
        if st.button("코드 선택기로 이동"):
            st.switch_page("run.py")
        st.stop()

    # 탭/쉼표 구분 파싱 (엑셀 복사는 보통 탭)
    def _parse_pasted(text: str) -> pd.DataFrame:
        for sep in ["\t", ",", ";"]:
            try:
                df = pd.read_csv(
                    io.StringIO(text.strip()),
                    sep=sep,
                    encoding="utf-8",
                    header=0 if has_header else None,
                )
                if not has_header and df.shape[1] >= 2:
                    df.columns = [f"컬럼{i+1}" for i in range(df.shape[1])]
                if df.shape[1] >= 2:
                    return df
            except Exception:
                continue
        return pd.read_csv(io.StringIO(text.strip()), sep=None, engine="python", encoding="utf-8", header=0 if has_header else None)

    try:
        df_raw = _parse_pasted(pasted_text)
    except Exception as e:
        st.error(f"파싱 실패: {e}")
        st.info("탭 또는 쉼표로 구분된 형식인지 확인해 주세요.")
        st.stop()

else:
    uploaded = st.file_uploader("엑셀 파일 업로드 (xlsx)", type=["xlsx"], key="excel_upload")
    if uploaded is None:
        st.info("엑셀 파일을 업로드해 주세요.")
        if st.button("코드 선택기로 이동"):
            st.switch_page("run.py")
        st.stop()

    try:
        df_raw = pd.read_excel(io.BytesIO(uploaded.getvalue()), sheet_name=0)
    except Exception as e:
        st.error(f"엑셀 로드 실패: {e}")
        st.info("DRM 등으로 업로드가 안 되면, 엑셀에서 데이터를 복사해 '텍스트 붙여넣기' 방식으로 시도해 보세요.")
        st.stop()

if df_raw is None or df_raw.empty:
    st.warning("데이터가 없습니다.")
    st.stop()

st.subheader("1. 데이터 미리보기")
st.write(f"총 **{len(df_raw)}**행, 컬럼: {list(df_raw.columns)}")

# CODE, NM 컬럼 매핑
cols = list(df_raw.columns)
code_idx = cols.index("CODE") if "CODE" in cols else 0
nm_idx = cols.index("NM") if "NM" in cols else (1 if len(cols) > 1 else 0)
code_col = st.selectbox(
    "CODE에 매핑할 컬럼",
    options=cols,
    index=min(code_idx, len(cols) - 1),
    key="code_col",
)
nm_col = st.selectbox(
    "NM에 매핑할 컬럼",
    options=cols,
    index=min(nm_idx, len(cols) - 1),
    key="nm_col",
)

df_preview = df_raw[[code_col, nm_col]].copy()
df_preview.columns = ["CODE", "NM"]
df_preview = df_preview.dropna(subset=["CODE"]).astype(str)

st.dataframe(df_preview.head(100), use_container_width=True, height=350)
if len(df_preview) > 100:
    st.caption(f"상위 100행만 표시 (전체 {len(df_preview)}행)")

st.divider()
st.subheader("2. DB 반영")

mode = st.radio(
    "반영 방식",
    ["replace (기존 데이터 전체 교체)", "append (기존 데이터에 추가, 중복 시 무시)"],
    index=0,
)
mode_val = "replace" if "replace" in mode.lower() else "append"

st.write("**db에 반영 할까요?**")
col_yes, col_no, _ = st.columns([1, 1, 2])
with col_yes:
    if st.button("예, 반영합니다", type="primary", use_container_width=True):
        try:
            inserted, message = import_risk_codes_to_db(df_preview, mode=mode_val)
            st.success(message)
            st.balloons()
        except Exception as e:
            st.error(f"반영 실패: {e}")
with col_no:
    st.button("아니오", use_container_width=True)  # 클릭해도 아무 동작 없음

st.divider()
if st.button("코드 선택기로 이동", use_container_width=True):
    st.switch_page("run.py")
