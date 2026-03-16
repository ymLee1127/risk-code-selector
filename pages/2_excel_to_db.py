"""엑셀 → DB 일괄 Import 페이지 (위험률/상품/담보)"""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from config.entity_types import ENTITY_TYPES, get_entity_config
from db.connection import import_entity_to_db, test_connection

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

# 엔티티 타입 선택
entity_type = st.radio(
    "대상 엔티티",
    options=list(ENTITY_TYPES.keys()),
    index=0,
    horizontal=True,
    key="excel_entity_type",
)

entity_cfg = get_entity_config(entity_type)
table_name = entity_cfg.get("table", "")
required_cols = entity_cfg.get("required_cols", set())
display_cols = entity_cfg.get("display_cols", [])
code_col = entity_cfg.get("code_col", "CODE")
name_col = entity_cfg.get("name_col", "NM")

st.caption(f"대상 테이블: **{table_name}** | 필수 컬럼: {', '.join(sorted(required_cols))}")

st.divider()

input_mode = st.radio(
    "데이터 입력 방식",
    ["텍스트 붙여넣기 (엑셀에서 복사)", "엑셀 파일 업로드"],
    index=0,
    horizontal=True,
)

df_raw = None

if input_mode == "텍스트 붙여넣기 (엑셀에서 복사)":
    hint = (
        f"엑셀에서 {code_col}, {name_col} 컬럼(또는 해당 데이터)을 선택한 뒤 Ctrl+C로 복사하고 아래에 붙여넣으세요."
        if entity_type == "위험률"
        else f"엑셀에서 {', '.join(display_cols[:5])}... 등 컬럼을 선택한 뒤 Ctrl+C로 복사하고 아래에 붙여넣으세요."
    )
    st.markdown(f"**{hint}**")
    st.markdown("- 첫 줄이 헤더(컬럼명)인 경우 자동 인식됩니다.")
    st.markdown("- 탭 또는 쉼표로 구분된 텍스트를 지원합니다.")
    has_header = st.checkbox("첫 줄이 헤더(컬럼명)입니다", value=True, key="has_header")
    # 100만 라인 지원: 라인당 ~500자 가정 → 5억 자
    pasted_text = st.text_area(
        "데이터 붙여넣기",
        placeholder="예시:\nCODE\tNM\nK001\t코드이름1\nK002\t코드이름2" if entity_type == "위험률" else f"예시:\n{code_col}\t{name_col}\t...\n값1\t값2\t...",
        height=500,
        max_chars=500_000_000,
        key="pasted_csv",
    )
    st.caption("💡 최대 약 100만 라인까지 붙여넣기 가능. 매우 큰 데이터는 '엑셀 파일 업로드'를 권장합니다.")
    if not pasted_text.strip():
        st.info("엑셀에서 복사한 데이터를 위 입력창에 붙여넣어 주세요.")
        if st.button("코드 선택기로 이동"):
            st.switch_page("run.py")
        st.stop()

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

# 컬럼 매핑
cols = list(df_raw.columns)
target_cols = [code_col, name_col] if entity_type == "위험률" else display_cols

col_mapping = {}
mapping_container = st.container() if entity_type == "위험률" else st.expander("컬럼 매핑 (상품/담보)", expanded=True)
with mapping_container:
    n_cols = 3
    for i, target in enumerate(target_cols):
        default_idx = cols.index(target) if target in cols else min(i, len(cols) - 1)
        col_mapping[target] = st.selectbox(
            f"→ {target}",
            options=cols,
            index=min(default_idx, len(cols) - 1),
            key=f"map_{entity_type}_{target}",
        )

# 매핑된 DataFrame 생성
df_preview = pd.DataFrame()
for target, source in col_mapping.items():
    df_preview[target] = df_raw[source].astype(str)

# 필수 컬럼 검증
missing = required_cols - set(df_preview.columns)
if missing:
    st.error(f"필수 컬럼 누락: {', '.join(sorted(missing))}")
    st.stop()

df_preview = df_preview.dropna(subset=[code_col])
df_preview = df_preview.drop_duplicates(subset=[code_col], keep="first")

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

st.write("**DB에 반영 할까요?**")
col_yes, col_no, _ = st.columns([1, 1, 2])
with col_yes:
    if st.button("예, 반영합니다", type="primary", use_container_width=True):
        try:
            inserted, message = import_entity_to_db(entity_type, df_preview, mode=mode_val)
            st.success(message)
            st.balloons()
        except Exception as e:
            st.error(f"반영 실패: {e}")
with col_no:
    st.button("아니오", use_container_width=True)

st.divider()
if st.button("코드 선택기로 이동", use_container_width=True):
    st.switch_page("run.py")
