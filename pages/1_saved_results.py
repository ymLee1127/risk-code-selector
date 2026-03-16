"""저장 결과 목록 페이지 - 위험률/상품/담보별 제목, 메모, 선택 코드/이름, 요약"""
import math
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from config.entity_types import ENTITY_TYPES, get_entity_config
from core.selection import load_saved_selection_sets
from data.loaders import load_by_entity

st.set_page_config(page_title="저장 결과 목록", layout="wide")

st.title("저장 결과 목록")
st.caption("저장된 선택 결과를 확인하고, 코드 선택기로 이동할 수 있습니다.")

# 엔티티 타입 탭
entity_type = st.radio(
    "엔티티 타입",
    options=list(ENTITY_TYPES.keys()),
    index=0,
    horizontal=True,
    key="saved_entity_type",
)

saved_items = load_saved_selection_sets(entity_type=entity_type)

# 이름/메모 검색
search_term = st.text_input("이름·메모 검색", placeholder="이름 또는 메모로 검색...", key="saved_search")
if search_term.strip():
    search_lower = search_term.strip().lower()
    saved_items = [
        item
        for item in saved_items
        if search_lower in (item.get("name", "") or "").lower()
        or search_lower in (item.get("description", "") or "").lower()
    ]

if not saved_items:
    st.info(
        f"[{entity_type}] 검색 결과가 없습니다." if search_term.strip()
        else f"[{entity_type}] 저장된 선택 결과가 없습니다."
    )
    if st.button("코드 선택기로 이동"):
        st.switch_page("run.py")
    st.stop()

# 엔티티별 코드→이름 매핑
entity_cfg = get_entity_config(entity_type)
code_col = entity_cfg["code_col"]
name_col = entity_cfg["name_col"]
try:
    df_master = load_by_entity(entity_type, source="default")
    code_to_nm = dict(zip(df_master[code_col].astype(str), df_master[name_col].astype(str)))
except Exception:
    code_to_nm = {}

# 요약
total_sets = len(saved_items)
total_codes = sum(len(item.get("codes", [])) for item in saved_items)
m1, m2, m3 = st.columns(3)
m1.metric(f"[{entity_type}] 저장 세트 수", total_sets)
m2.metric("총 선택 코드 수", total_codes)
m3.metric("평균 코드/세트", round(total_codes / total_sets, 1) if total_sets else 0)

st.divider()

for item in saved_items:
    name = item.get("name", "")
    item_entity = item.get("entity_type", "위험률")
    description = item.get("description", "") or "(없음)"
    codes = item.get("codes", [])
    saved_at = item.get("saved_at", "")

    # 접힌 상태에서 보일 라벨: 이름, 건수, 날짜, 메모
    memo_preview = description[:40] + "..." if len(description) > 40 else description
    label = f"**{name}** | {len(codes)}건 | {saved_at} | 메모: {memo_preview}"

    with st.expander(label, expanded=False):
        st.markdown("#### 제목")
        st.write(name)

        st.markdown("#### 메모")
        st.write(description)

        st.markdown("#### 선택 코드 목록")
        if codes:
            # 엔티티별 코드·이름 테이블
            rows = []
            for code in codes:
                code_str = str(code)
                nm = code_to_nm.get(code_str, "-")
                rows.append({code_col: code_str, name_col: nm})
            tbl = pd.DataFrame(rows)

            # 페이지네이션
            page_size = st.selectbox(
                "페이지당 행 수",
                [20, 50, 100, 200],
                index=0,
                key=f"page_size_{entity_type}_{name}",
            )
            total_rows = len(rows)
            total_pages = max(1, math.ceil(total_rows / page_size))
            page_key = f"saved_code_page_{entity_type}_{name}"
            if page_key not in st.session_state:
                st.session_state[page_key] = 1
            current_page = st.session_state[page_key]
            current_page = max(1, min(current_page, total_pages))
            st.session_state[page_key] = current_page

            start_idx = (current_page - 1) * page_size
            end_idx = start_idx + page_size
            page_rows = rows[start_idx:end_idx]
            page_tbl = pd.DataFrame(page_rows)

            st.dataframe(page_tbl, use_container_width=True, height=min(300, 50 + len(page_rows) * 35))

            # 페이지 네비게이션
            nav_col1, nav_col2, nav_col3, nav_col4 = st.columns([1, 1, 2, 2])
            with nav_col1:
                if st.button("◀ 이전", key=f"prev_{entity_type}_{name}", use_container_width=True):
                    st.session_state[page_key] = max(1, current_page - 1)
                    st.rerun()
            with nav_col2:
                if st.button("다음 ▶", key=f"next_{entity_type}_{name}", use_container_width=True):
                    st.session_state[page_key] = min(total_pages, current_page + 1)
                    st.rerun()
            with nav_col3:
                st.caption(f"페이지 {current_page} / {total_pages}")
            with nav_col4:
                st.caption(f"총 **{len(codes)}**개 코드 (현재 {start_idx + 1}~{min(end_idx, total_rows)})")
        else:
            st.caption("선택된 코드가 없습니다.")

        if st.button("코드 선택기로 이동", key=f"go_{entity_type}_{name}", use_container_width=True):
            st.session_state.load_from_saved_page = name
            st.session_state.load_from_saved_entity_type = item_entity
            st.switch_page("run.py")

st.divider()
if st.button("코드 선택기로 이동 (홈)", use_container_width=True):
    st.switch_page("run.py")
