"""Streamlit 위험률 코드 선택기 앱"""
import math
import re

import pandas as pd
import streamlit as st

from config import settings
from core.regex_utils import (
    build_patterns_from_lines,
    build_pos_regex,
    build_neg_regex,
    evaluate_text,
    merge_regex_patterns,
)
from core.filter import first_pass_filter, paginate_df
from core.selection import (
    build_to_query_string,
    load_saved_selection_sets,
    upsert_selection_set,
)
from data.loaders import (
    FALLBACK_SAMPLE,
    load_default_data,
    load_from_db,
    load_from_uploaded_file,
)
from db.connection import test_connection


# =========================
# session_state
# =========================
def init_regex_state():
    if "keyword" not in st.session_state:
        st.session_state.keyword = ""  # 최초: 빈값 (초기화 상태)
    if "last_keyword_for_regex" not in st.session_state:
        st.session_state.last_keyword_for_regex = ""
    if "pos_regex" not in st.session_state:
        st.session_state.pos_regex = ""
    if "neg_regex" not in st.session_state:
        st.session_state.neg_regex = ""
    if "extra_pos_patterns_text" not in st.session_state:
        st.session_state.extra_pos_patterns_text = ""
    if "extra_neg_patterns_text" not in st.session_state:
        st.session_state.extra_neg_patterns_text = ""
    if "top_filter" not in st.session_state:
        st.session_state.top_filter = "전체"
    if "current_page" not in st.session_state:
        st.session_state.current_page = 1
    if "selection_map" not in st.session_state:
        st.session_state.selection_map = {}
    if "last_loaded_codes" not in st.session_state:
        st.session_state.last_loaded_codes = set()
    if "test_text" not in st.session_state:
        st.session_state.test_text = ""
    if "save_name" not in st.session_state:
        st.session_state.save_name = ""
    if "save_description" not in st.session_state:
        st.session_state.save_description = ""

    saved_items = load_saved_selection_sets()
    if "saved_selection_names" not in st.session_state:
        st.session_state.saved_selection_names = [item.get("name", "") for item in saved_items]
    if "selected_saved_name" not in st.session_state:
        st.session_state.selected_saved_name = (
            st.session_state.saved_selection_names[0] if st.session_state.saved_selection_names else ""
        )


def refresh_saved_selection_state():
    saved_items = load_saved_selection_sets()
    names = [item.get("name", "") for item in saved_items]
    st.session_state.saved_selection_names = names
    if names:
        if st.session_state.get("selected_saved_name", "") not in names:
            st.session_state.selected_saved_name = names[0]
    else:
        st.session_state.selected_saved_name = ""


def reset_filter_state():
    """필터 관련 상태 리셋 (최종선택은 유지)"""
    st.session_state.pos_regex = ""
    st.session_state.neg_regex = ""
    st.session_state.extra_pos_patterns_text = ""
    st.session_state.extra_neg_patterns_text = ""
    st.session_state.last_keyword_for_regex = ""
    st.session_state.top_filter = "전체"
    st.session_state.current_page = 1


def sync_regex_with_keyword():
    current_keyword = st.session_state.keyword.strip()
    last_keyword = st.session_state.last_keyword_for_regex.strip()

    if not current_keyword:
        # 키워드 비우고 Enter → 필터 리셋 (최종선택 유지)
        reset_filter_state()
        return

    if current_keyword != last_keyword:
        st.session_state.pos_regex = build_pos_regex(current_keyword)
        st.session_state.neg_regex = build_neg_regex(current_keyword)
        st.session_state.last_keyword_for_regex = current_keyword
        st.session_state.current_page = 1


def init_selection_state(df_filtered: pd.DataFrame):
    """데이터 로드 시 선택 상태 초기화. 최초 로딩 시에는 아무것도 선택되지 않은 상태."""
    current_codes = set(df_filtered["CODE"].astype(str).tolist())
    last_codes = st.session_state.last_loaded_codes
    new_codes = current_codes - last_codes
    for code in new_codes:
        st.session_state.selection_map[code] = False  # 최초 로딩 시 선택 없음
    st.session_state.last_loaded_codes = current_codes


def reset_selection_to_recommendation(df_filtered: pd.DataFrame):
    for _, row in df_filtered.iterrows():
        st.session_state.selection_map[row["CODE"]] = bool(row["추천포함"])


def set_top_filter(filter_name: str):
    st.session_state.top_filter = filter_name
    st.session_state.current_page = 1


def ensure_page_in_range(page: int, total_pages: int) -> int:
    if total_pages <= 0:
        return 1
    return max(1, min(page, total_pages))


def load_saved_selection_into_map(selected_name: str, df: pd.DataFrame):
    """저장된 선택을 selection_map에 반영. df는 전체 데이터(필터 전)를 사용해 모든 코드에 적용."""
    saved_items = load_saved_selection_sets()
    target = next((item for item in saved_items if item.get("name") == selected_name), None)
    if target is None:
        raise ValueError("선택한 저장 항목을 찾을 수 없습니다.")
    saved_codes = set(str(c) for c in target.get("codes", []))
    all_codes = set(df["CODE"].astype(str).tolist())
    for code in all_codes:
        st.session_state.selection_map[code] = code in saved_codes


# =========================
# Dialogs
# =========================
@st.dialog("패턴 테스트")
def pattern_test_dialog(final_pos_regex: str, final_neg_regex: str):
    st.markdown("### 최종 적용 정규식")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**최종 긍정 패턴**")
        st.code(final_pos_regex if final_pos_regex.strip() else "(없음)")
    with c2:
        st.markdown("**최종 부정 패턴**")
        st.code(final_neg_regex if final_neg_regex.strip() else "(없음)")

    st.divider()
    test_text = st.text_input(
        "테스트할 문구를 입력하세요",
        value=st.session_state.get("test_text", ""),
        key="dialog_test_text",
        placeholder="예: 치아파절포함(치조골제외)",
    )

    if test_text.strip():
        try:
            test_result = evaluate_text(
                test_text,
                st.session_state.keyword,
                final_pos_regex,
                final_neg_regex,
            )
            st.session_state.test_text = test_text
            tc1, tc2, tc3, tc4 = st.columns(4)
            tc1.metric("키워드 포함", "Y" if test_result["has_keyword"] else "N")
            tc2.metric("긍정 매칭", "Y" if test_result["pos_match"] else "N")
            tc3.metric("부정 매칭", "Y" if test_result["neg_match"] else "N")
            tc4.metric("추천 포함", "Y" if test_result["추천포함"] else "N")
            st.write(f"판단근거: **{test_result['판단근거']}**")
            with st.expander("테스트 상세 보기"):
                st.json(test_result)
        except re.error as e:
            st.error(f"테스트 중 정규식 오류: {e}")


@st.dialog("to_query")
def to_query_dialog(query_text: str):
    st.markdown("### 쿼리 조건용 CODE 문자열")
    st.code(query_text, language="sql")
    st.text_area("복사용 문자열", value=query_text, height=120, key="to_query_text_area")
    st.caption("위 문자열을 복사해서 SQL IN 조건 등에 사용하세요.")


# =========================
# Main App
# =========================
def run_streamlit_app() -> None:
    st.set_page_config(page_title="위험률 코드 선택기", layout="wide")
    init_regex_state()
    refresh_saved_selection_state()

    st.title("위험률 코드 선택기")
    st.caption("정규식 1차 필터 + 페이지 검토 + 체크박스 최종 선택")

    with st.sidebar:
        if st.button("📋 저장 결과 목록", use_container_width=True):
            st.switch_page("pages/1_saved_results.py")
        if st.button("📥 엑셀 → DB Import", use_container_width=True):
            st.switch_page("pages/2_excel_to_db.py")
        st.divider()
        st.header("데이터 소스")

        source_type = st.radio(
            "불러오기 방식",
            ["기본 엑셀 파일", "파일 업로드", "DB 연결"],
            index=0,
        )

        uploaded = None
        db_table = None
        db_code_col = None
        db_nm_col = None

        if source_type == "기본 엑셀 파일":
            st.write(f"기본 경로: `{settings.DEFAULT_EXCEL_PATH}`")
            st.caption("해당 파일이 있으면 자동으로 읽고, 없으면 샘플 데이터를 사용합니다.")
        elif source_type == "파일 업로드":
            uploaded = st.file_uploader("CSV 또는 Excel 업로드", type=["csv", "xlsx"])
        else:
            # DB 연결
            ok, msg = test_connection()
            if ok:
                st.success(f"DB 연결: {msg}")
            else:
                st.error(f"DB 연결 실패: {msg}")
            st.caption(f"URL: `{settings.DATABASE_URL[:50]}...`" if len(settings.DATABASE_URL) > 50 else f"URL: `{settings.DATABASE_URL}`")
            db_table = st.text_input("테이블명", value=settings.DB_RISK_CODE_TABLE, key="db_table")
            db_code_col = st.text_input("CODE 컬럼", value=settings.DB_CODE_COLUMN, key="db_code_col")
            db_nm_col = st.text_input("NM 컬럼", value=settings.DB_NM_COLUMN, key="db_nm_col")

        st.divider()
        st.header("1차 필터 설정")

        st.text_input(
            "키워드",
            key="keyword",
            on_change=sync_regex_with_keyword,
            placeholder="예: 치아파절 (입력 후 Enter)",
        )

        st.markdown("**기본 긍정 정규식**")
        st.text_area("긍정 패턴", key="pos_regex", height=90)

        st.markdown("**추가 긍정 패턴**")
        st.text_area(
            "추가 긍정 패턴(줄바꿈으로 여러 개 입력)",
            key="extra_pos_patterns_text",
            height=100,
            help="한 줄에 하나씩 입력하세요. 예: 영구치파절",
        )

        st.markdown("**기본 부정 정규식**")
        st.text_area("부정 패턴", key="neg_regex", height=110)

        st.markdown("**추가 부정 패턴**")
        st.text_area(
            "추가 부정 패턴(줄바꿈으로 여러 개 입력)",
            key="extra_neg_patterns_text",
            height=120,
            help="한 줄에 하나씩 입력하세요. 예: 대장용종.{0,4}제외",
        )

        st.divider()
        st.header("보기 옵션")

        only_review_needed = st.checkbox("검토 필요만 보기", value=False)
        only_selected = st.checkbox("최종 선택만 보기", value=False)
        page_size = st.selectbox("페이지당 행 수", [50, 100, 200, 500], index=1)

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            open_pattern_test = st.button("패턴 테스트", use_container_width=True)
        with btn_col2:
            if st.button("상단 필터 해제", use_container_width=True):
                set_top_filter("전체")
                st.rerun()

    # 최종 정규식
    extra_pos_patterns = build_patterns_from_lines(st.session_state.extra_pos_patterns_text)
    extra_neg_patterns = build_patterns_from_lines(st.session_state.extra_neg_patterns_text)
    final_pos_regex = merge_regex_patterns(st.session_state.pos_regex, extra_pos_patterns)
    final_neg_regex = merge_regex_patterns(st.session_state.neg_regex, extra_neg_patterns)

    if open_pattern_test:
        pattern_test_dialog(final_pos_regex, final_neg_regex)

    # 데이터 로드
    try:
        if source_type == "기본 엑셀 파일":
            df = load_default_data()
        elif source_type == "파일 업로드":
            if uploaded is None:
                st.info("업로드 파일이 없어서 샘플 데이터를 사용합니다.")
                df = FALLBACK_SAMPLE.copy()
            else:
                df = load_from_uploaded_file(uploaded.name, uploaded.getvalue())
        else:
            df = load_from_db(
                table=db_table or settings.DB_RISK_CODE_TABLE,
                code_col=db_code_col or settings.DB_CODE_COLUMN,
                nm_col=db_nm_col or settings.DB_NM_COLUMN,
            )

        filtered = first_pass_filter(
            df,
            st.session_state.keyword,
            final_pos_regex,
            final_neg_regex,
        )
    except re.error as e:
        st.error(f"정규식 오류: {e}")
        st.stop()
    except Exception as e:
        st.error(str(e))
        st.stop()

    init_selection_state(filtered)

    # 저장결과 목록 페이지에서 "코드 선택기로 이동" 클릭 시 불러오기
    load_from_page = st.session_state.pop("load_from_saved_page", None)
    if load_from_page:
        try:
            load_saved_selection_into_map(load_from_page, df)
            set_top_filter("최종선택")
            st.session_state.selected_saved_name = load_from_page
            st.toast(f"'{load_from_page}' 불러오기 완료")
        except Exception as e:
            st.error(f"불러오기 실패: {e}")

    # 상단 요약
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("전체 건수", len(filtered))
        if st.button("전체 보기", key="btn_all", use_container_width=True):
            set_top_filter("전체")
            st.rerun()
    with m2:
        # 키워드 없으면 초기화 상태 (추천/부정 없음). 키워드 입력 후 Enter 시 추천/부정 표시
        is_init_state = not st.session_state.keyword.strip()
        reco_count = 0 if is_init_state else int(filtered["추천포함"].sum())
        st.metric("추천 포함", reco_count)
        if st.button("추천 포함만 보기", key="btn_reco", use_container_width=True):
            set_top_filter("추천포함")
            st.rerun()
    with m3:
        neg_count = 0 if is_init_state else int(filtered["neg_match"].sum())
        st.metric("부정 패턴", neg_count)
        if st.button("부정 패턴만 보기", key="btn_neg", use_container_width=True):
            set_top_filter("부정패턴")
            st.rerun()
    with m4:
        st.metric("최종 선택", sum(st.session_state.selection_map.values()))
        if st.button("최종 선택만 보기", key="btn_selected_top", use_container_width=True):
            set_top_filter("최종선택")
            st.rerun()

    st.caption(f"현재 상단 필터: **{st.session_state.top_filter}**")
    st.divider()

    left, right = st.columns([1.7, 1])

    with left:
        st.subheader("후보 목록")
        view = filtered.copy()

        if st.session_state.top_filter == "추천포함":
            view = view[view["추천포함"]]
        elif st.session_state.top_filter == "부정패턴":
            view = view[view["neg_match"]]
        elif st.session_state.top_filter == "최종선택":
            selected_codes = {k for k, v in st.session_state.selection_map.items() if v}
            view = view[view["CODE"].isin(selected_codes)]

        if only_review_needed:
            view = view[view["검토필요"]]
        if only_selected:
            selected_codes = {k for k, v in st.session_state.selection_map.items() if v}
            view = view[view["CODE"].isin(selected_codes)]

        search_term = st.text_input("리스트 내 검색", value="")
        if search_term.strip():
            mask = (
                view["NM"].astype(str).str.contains(search_term, na=False)
                | view["CODE"].astype(str).str.contains(search_term, na=False)
            )
            view = view[mask]

        view = view.reset_index(drop=True)
        total_rows = len(view)
        total_pages = max(1, math.ceil(total_rows / page_size))
        st.session_state.current_page = ensure_page_in_range(
            st.session_state.current_page, total_pages
        )

        nav1, nav2, nav3, nav4, nav5 = st.columns([1, 1, 2, 2, 3])
        with nav1:
            if st.button("⏮ 처음", use_container_width=True):
                st.session_state.current_page = 1
                st.rerun()
        with nav2:
            if st.button("◀ 이전", use_container_width=True):
                st.session_state.current_page = max(1, st.session_state.current_page - 1)
                st.rerun()
        with nav3:
            page_input = st.number_input(
                "페이지",
                min_value=1,
                max_value=total_pages,
                value=st.session_state.current_page,
                step=1,
            )
            if page_input != st.session_state.current_page:
                st.session_state.current_page = int(page_input)
                st.rerun()
        with nav4:
            st.write("")
            st.write(f"총 {total_pages:,} 페이지")
        with nav5:
            start_no = (st.session_state.current_page - 1) * page_size + 1 if total_rows > 0 else 0
            end_no = min(st.session_state.current_page * page_size, total_rows)
            st.write("")
            st.write(f"현재 {start_no:,} ~ {end_no:,} / {total_rows:,}")

        page_df = paginate_df(view, st.session_state.current_page, page_size)

        batch_cols = st.columns(3)
        with batch_cols[0]:
            if st.button("현재 페이지 전체 선택", use_container_width=True):
                for code in page_df["CODE"].tolist():
                    st.session_state.selection_map[code] = True
                st.rerun()
        with batch_cols[1]:
            if st.button("현재 페이지 전체 해제", use_container_width=True):
                for code in page_df["CODE"].tolist():
                    st.session_state.selection_map[code] = False
                st.rerun()
        with batch_cols[2]:
            if st.button("추천 결과로 초기화", use_container_width=True):
                reset_selection_to_recommendation(filtered)
                st.rerun()

        st.caption("현재 페이지에서 체크를 조정해도 전체 페이지의 선택 상태는 유지됩니다.")

        header = st.columns([0.8, 1.4, 5.8, 1.0, 1.0, 1.5])
        header[0].markdown("**선택**")
        header[1].markdown("**CODE**")
        header[2].markdown("**NM**")
        header[3].markdown("**추천**")
        header[4].markdown("**부정**")
        header[5].markdown("**판단근거**")

        for _, row in page_df.iterrows():
            code = row["CODE"]
            cols = st.columns([0.8, 1.4, 5.8, 1.0, 1.0, 1.5])
            checked = cols[0].checkbox(
                "select",
                value=st.session_state.selection_map.get(code, False),
                key=f"chk_{code}",
                label_visibility="collapsed",
            )
            st.session_state.selection_map[code] = checked
            cols[1].write(code)
            cols[2].write(row["NM"])
            # 초기화 상태(전체)에서는 추천/부정/판단근거 표기 없음
            if is_init_state:
                cols[3].write("")
                cols[4].write("")
                cols[5].write("")
            else:
                cols[3].write("Y" if row["추천포함"] else "")
                cols[4].write("Y" if row["neg_match"] else "")
                cols[5].write(row["판단근거"])

    with right:
        st.subheader("최종 선택 결과")
        selected_codes = [k for k, v in st.session_state.selection_map.items() if v]
        # filtered에 있는 선택 코드 + filtered에 없지만 df에 있는 선택 코드 (불러오기 시 전체 반영)
        in_filtered = filtered[filtered["CODE"].isin(selected_codes)][
            ["CODE", "NM", "추천포함", "판단근거"]
        ].copy()
        missing_codes = set(selected_codes) - set(filtered["CODE"].astype(str))
        if missing_codes:
            missing_df = df[df["CODE"].astype(str).isin(missing_codes)].copy()
            missing_df = missing_df[["CODE", "NM"]].copy()
            missing_df["추천포함"] = False
            missing_df["판단근거"] = "필터범위외"
            result_df = pd.concat([in_filtered, missing_df], ignore_index=True)
        else:
            result_df = in_filtered
        result_df = result_df.sort_values(["추천포함", "CODE"], ascending=[False, True])

        st.dataframe(result_df, use_container_width=True, height=420)

        action_col1, action_col2 = st.columns(2)
        with action_col1:
            csv_bytes = result_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="최종 선택 CSV 다운로드",
                data=csv_bytes,
                file_name="selected_risk_codes.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with action_col2:
            if st.button("to_query", use_container_width=True):
                query_text = build_to_query_string(result_df["CODE"].astype(str).tolist())
                to_query_dialog(query_text)

        st.markdown("### 선택 결과 저장")
        st.text_input("저장 이름", key="save_name", placeholder="예: 치아파절_1차선정")
        st.text_input("설명", key="save_description", placeholder="예: 2026-03-13 오전 검토본")

        if st.button("현재 선택 결과 저장", use_container_width=True):
            save_name = st.session_state.save_name.strip()
            save_description = st.session_state.save_description.strip()
            if not save_name:
                st.warning("저장 이름을 입력하세요.")
            else:
                upsert_selection_set(
                    name=save_name,
                    description=save_description,
                    codes=result_df["CODE"].astype(str).tolist(),
                )
                refresh_saved_selection_state()
                st.session_state.selected_saved_name = save_name
                st.success(f"'{save_name}' 저장 완료")
                st.rerun()

        st.markdown("### 저장 결과 불러오기")
        saved_items = load_saved_selection_sets()
        saved_names = [item.get("name", "") for item in saved_items]

        if saved_names:
            selected_saved_name = st.selectbox(
                "저장 항목 선택",
                options=saved_names,
                index=saved_names.index(st.session_state.selected_saved_name)
                if st.session_state.selected_saved_name in saved_names
                else 0,
                key="selected_saved_name",
            )
            selected_item = next(
                (item for item in saved_items if item.get("name") == selected_saved_name),
                None,
            )
            if selected_item:
                st.caption(
                    f"설명: {selected_item.get('description', '')} | "
                    f"건수: {len(selected_item.get('codes', []))} | "
                    f"저장시각: {selected_item.get('saved_at', '')}"
                )
            if st.button("불러오기", use_container_width=True):
                try:
                    load_saved_selection_into_map(selected_saved_name, df)
                    set_top_filter("최종선택")  # 불러온 결과를 목록/최종선택에 바로 반영
                    st.success(f"'{selected_saved_name}' 불러오기 완료")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        else:
            st.caption("저장된 선택 결과가 없습니다.")

        st.markdown("### 사용 흐름")
        st.markdown(
            """
1. 키워드를 입력하면 기본 긍정/부정 패턴이 자동 생성됩니다.  
2. 추가 긍정/부정 패턴을 여러 줄로 입력해 예외를 확장합니다.  
3. **패턴 테스트** 버튼을 누르면 팝업에서 문구를 검증합니다.  
4. 상단 필터로 추천/부정/최종선택만 빠르게 좁혀봅니다.  
5. 페이지를 넘기며 체크박스로 최종 조정합니다.  
6. 최종 결과를 CSV로 저장하거나 `to_query` 문자열로 변환합니다.  
7. 최종 선택 결과를 이름/설명과 함께 저장하고 나중에 다시 불러올 수 있습니다.
            """
        )

    st.divider()
    with st.expander("정규식 팁"):
        st.markdown(
            r"""
- `|` 는 OR 조건입니다.  
- 추가 패턴은 한 줄에 하나씩 넣으면 자동으로 합쳐집니다.  
- `대장용종.{0,4}제외` 는 `대장용종` 뒤 0~4글자 안에 `제외`가 있으면 매칭합니다.  
- 기본 패턴은 키워드에 맞춰 자동 변경되고, 추가 패턴은 유지됩니다.  
- 너무 넓은 패턴은 과매칭할 수 있으니 패턴 테스트 팝업에서 꼭 확인하세요.
            """
        )
