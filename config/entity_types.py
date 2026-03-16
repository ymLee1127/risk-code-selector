"""
엔티티 타입별 설정 (위험률, 상품, 담보)

검색 방식:
- 위험률: NM 기반 정규식 (긍정/부정 패턴)
- 상품/담보: 이름 + 파라미터 조합 검색

1차 필터 항목 추가 (상품/담보):
  param_cols에 컬럼명을 추가하면 사이드바에 필터 입력란이 생깁니다.
  예: param_cols = ["파라미터보험기간", "파라미터납입주기", "상품코드", "외부번호"]
  ※ display_cols에 있는 컬럼만 사용 가능합니다.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ENTITY_TYPES = {
    "위험률": {
        "code_col": "CODE",
        "name_col": "NM",
        "search_mode": "regex",
        "search_cols": ["NM"],
        "param_cols": [],
        "display_cols": ["CODE", "NM"],
        "table": "risk_code_master",
        "excel_path": str(PROJECT_ROOT / "risk_code_master.xlsx"),
        "required_cols": {"CODE", "NM"},
    },
    "상품": {
        "code_col": "상품코드",
        "name_col": "상품명",
        "search_mode": "keyword_combo",
        "search_cols": ["상품명", "파라미터보험기간코드", "파라미터납입주기코드", "파라미터상품유형코드","상품코드RD"],
        "param_cols": [ "파라미터보험기간코드", "파라미터납입주기코드", "파라미터상품유형코드","상품코드RD"],
        "display_cols": [
            "CI",
            "외부번호",
            "상품코드RD",
            "파라미터보험기간코드",
            "파라미터납입주기코드",
            "파라미터건강상태코드",
            "파라미터상품종목코드",
            "파라미터상품유형코드",
            "파라미터개인가족구분코드",
            "파라미터연금지급유형코드",
            "파라미터고액구분코드",
            "파라미터이전상품코드",
            "파라미터단체개별전환구분코드",
            "파라미터채널구분코드",
            "이전상품코드",
            "상품명",
            "약식용도상품명",
            "영문상품명",
            "증권용도상품명",
            "안내장용도상품명",
            "템플릿ID",
            "생성자",
            "생성일",
            "생성시간",
            "변경자",
            "변경일",
            "변경시간",
            "삭제여부"
            

        ],
        "table": "product_master",
        "excel_path": str(PROJECT_ROOT / "product_master.xlsx"),
        "required_cols": {"상품코드", "상품명"},
    },
    "담보": {
        "code_col": "담보코드RD",
        "name_col": "보험명",
        "search_mode": "keyword_combo",
        "search_cols": [
            "보험명",
            "파라미터주피보험자건강상태코드",
            "파라미터보험유형코드",
            "이전보험코드",
        ],
        "param_cols": ["파라미터주피보험자건강상태코드", "파라미터보험유형코드", "이전보험코드"],
        "display_cols": [
            "CI",
            "외부번호",
            "담보코드RD",
            "보험버전코드",
            "이전보험코드",
            "이전버전코드",
            "파라미터보험기간코드",
            "파라미터납입주기코드",
            "파라미터주피보험자건강상태코드",
            "파라미터계약관점피보험자유형코드",
            "파라미터자녀일련번호코드",
            "파라미터전환구분코드",
            "파라미터단체개벌전환구분코드",
            "파라미터담보종목코드",
            "파라미터갱신최대연령코드",
            "파라미터보험유형코드",
            "파라미터개인가족구분코드",
            "파라미터고액구분코드",
            "파라미터보험구분코드",
            "파라미터표준이율코드",
            "파라미터표준해약공제여부",
            "파라미터이전보험코드",
            "파라미터이전버전코드",
            "파라미터채널구분코드",
            "보험명",
            "약식용도보험명",
            "증권용도보험명",
            "템플릿ID",
            "생성자",
            "생성일",
            "생성시간",
            "변경자",
            "변경일",
            "변경시간",
            "삭제여부",
        ],
        "table": "coverage_master",
        "excel_path": str(PROJECT_ROOT / "coverage_master.xlsx"),
        "required_cols": {"담보코드RD", "보험명"},
    },
}


def get_entity_config(entity_type: str) -> dict:
    """엔티티 타입 설정 반환"""
    if entity_type not in ENTITY_TYPES:
        raise ValueError(f"알 수 없는 엔티티: {entity_type}")
    return ENTITY_TYPES[entity_type].copy()


def get_code_col(entity_type: str) -> str:
    return ENTITY_TYPES[entity_type]["code_col"]


def get_name_col(entity_type: str) -> str:
    return ENTITY_TYPES[entity_type]["name_col"]


def get_search_mode(entity_type: str) -> str:
    return ENTITY_TYPES[entity_type]["search_mode"]
