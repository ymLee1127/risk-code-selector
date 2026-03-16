"""상품/담보용 키워드+파라미터 조합 필터"""
import re

import pandas as pd


def filter_keyword_combo(
    df: pd.DataFrame,
    config: dict,
    keyword: str = "",
    param_filters: dict | None = None,
) -> pd.DataFrame:
    """
    이름 + 파라미터 조합 검색.
    config: entity_types의 엔티티 설정
    param_filters: {"파라미터보험기간": "10", "파라미터납입주기": "월납"} 등
    """
    code_col = config["code_col"]
    name_col = config["name_col"]
    search_cols = config.get("search_cols", [name_col])
    param_cols = config.get("param_cols", [])

    required = {code_col, name_col}
    if not required.issubset(df.columns):
        missing = required - set(df.columns)
        raise ValueError(f"필수 컬럼 누락: {', '.join(sorted(missing))}")

    temp = df.copy()
    temp[code_col] = temp[code_col].astype(str)

    keyword = (keyword or "").strip()
    param_filters = param_filters or {}

    # 검색 대상 컬럼들을 하나의 문자열로 합쳐서 검색
    def _search_text(row) -> str:
        parts = []
        for col in search_cols:
            if col in row.index and pd.notna(row[col]):
                parts.append(str(row[col]))
        return " ".join(parts)

    temp["_search_text"] = temp.apply(_search_text, axis=1)

    # 키워드 검색 (포함)
    if keyword:
        temp["has_keyword"] = temp["_search_text"].str.contains(
            re.escape(keyword), regex=True, na=False
        )
    else:
        temp["has_keyword"] = True

    # 파라미터 필터 (정확/부분 매칭)
    param_match = pd.Series([True] * len(temp), index=temp.index)
    for col, val in param_filters.items():
        if not val or col not in temp.columns:
            continue
        val_str = str(val).strip()
        param_match &= temp[col].astype(str).str.contains(val_str, regex=False, na=False)

    temp["param_match"] = param_match

    # 추천: 키워드 + 파라미터 모두 만족
    temp["추천포함"] = temp["has_keyword"] & temp["param_match"]
    temp["검토필요"] = temp["has_keyword"] & (~temp["param_match"])
    temp["neg_match"] = False  # keyword_combo에는 부정 패턴 없음
    temp["pos_match"] = temp["추천포함"]

    # 판단근거
    def _reason(row):
        if not row["has_keyword"]:
            return "키워드없음"
        if not row["param_match"]:
            return "파라미터불일치"
        return "조건일치"

    temp["판단근거"] = temp.apply(_reason, axis=1)
    temp = temp.drop(columns=["_search_text"], errors="ignore")
    # 앱 호환: CODE/NM 별칭 추가
    temp["CODE"] = temp[code_col].astype(str)
    temp["NM"] = temp[name_col].astype(str)
    return temp
