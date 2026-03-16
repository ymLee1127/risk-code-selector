"""필터링 로직 (위험률 정규식 + 공통)"""
import re

import pandas as pd

from core.regex_utils import compile_regex, normalize_text


def apply_filter(
    df: pd.DataFrame,
    entity_type: str,
    keyword: str = "",
    pos_regex: str = "",
    neg_regex: str = "",
    param_filters: dict | None = None,
) -> pd.DataFrame:
    """엔티티 타입에 따라 적절한 필터 적용"""
    from config.entity_types import get_entity_config, get_search_mode

    config = get_entity_config(entity_type)
    mode = get_search_mode(entity_type)

    if mode == "regex":
        # 위험률: CODE, NM 표준화 후 first_pass_filter
        df_std = df.copy()
        code_col = config["code_col"]
        name_col = config["name_col"]
        if code_col not in df_std.columns or name_col not in df_std.columns:
            raise ValueError(f"필수 컬럼 누락: {code_col}, {name_col}")
        df_std["CODE"] = df_std[code_col].astype(str)
        df_std["NM"] = df_std[name_col].astype(str)
        result = first_pass_filter(df_std, keyword, pos_regex, neg_regex)
        result[code_col] = result["CODE"]
        result[name_col] = result["NM"]
        return result

    from core.filter_keyword_combo import filter_keyword_combo

    return filter_keyword_combo(df, config, keyword, param_filters)


def build_reason(row: pd.Series) -> str:
    if not row["has_keyword"]:
        return "키워드없음"
    if row["neg_match"]:
        return "부정패턴매칭"
    if row["pos_match"]:
        return "긍정패턴매칭"
    return "검토필요"


def first_pass_filter(
    df: pd.DataFrame, keyword: str, pos_regex: str, neg_regex: str
) -> pd.DataFrame:
    required_cols = {"CODE", "NM"}
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        raise ValueError(f"필수 컬럼 누락: {', '.join(sorted(missing))}")

    temp = df.copy()
    temp["CODE"] = temp["CODE"].astype(str)
    temp["NM"] = temp["NM"].astype(str)
    temp["NM_CLEAN"] = temp["NM"].apply(normalize_text)

    keyword = (keyword or "").strip()
    temp["has_keyword"] = (
        temp["NM_CLEAN"].str.contains(re.escape(keyword), regex=True, na=False)
        if keyword
        else True
    )

    pos_compiled = compile_regex(pos_regex)
    neg_compiled = compile_regex(neg_regex)

    temp["pos_match"] = temp["NM_CLEAN"].apply(
        lambda x: bool(pos_compiled.search(x)) if pos_compiled else True
    )
    temp["neg_match"] = temp["NM_CLEAN"].apply(
        lambda x: bool(neg_compiled.search(x)) if neg_compiled else False
    )

    temp["추천포함"] = temp["has_keyword"] & temp["pos_match"] & (~temp["neg_match"])
    temp["검토필요"] = temp["has_keyword"] & (~temp["neg_match"]) & (~temp["pos_match"])
    temp["판단근거"] = temp.apply(build_reason, axis=1)

    return temp


def paginate_df(df: pd.DataFrame, page: int, page_size: int) -> pd.DataFrame:
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    return df.iloc[start_idx:end_idx]
