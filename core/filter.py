"""필터링 로직"""
import re

import pandas as pd

from core.regex_utils import compile_regex, normalize_text


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
