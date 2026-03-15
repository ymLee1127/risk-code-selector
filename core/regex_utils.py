"""정규식 관련 유틸"""
import re
from typing import List, Optional

DEFAULT_POS_REGEX_TEMPLATE = r"{keyword}(포함|은포함|발생|발생율)?"
DEFAULT_NEG_REGEX_TEMPLATE = (
    r"{keyword}.{{0,4}}(제외|아님|미포함|불포함|비대상)|{keyword}제외|{keyword}아님"
)


def build_pos_regex(keyword: str) -> str:
    keyword = re.escape((keyword or "").strip())
    if not keyword:
        return ""
    return DEFAULT_POS_REGEX_TEMPLATE.format(keyword=keyword)


def build_neg_regex(keyword: str) -> str:
    keyword = re.escape((keyword or "").strip())
    if not keyword:
        return ""
    return DEFAULT_NEG_REGEX_TEMPLATE.format(keyword=keyword)


def build_patterns_from_lines(text: str) -> List[str]:
    if not text:
        return []
    return [line.strip() for line in str(text).splitlines() if line.strip()]


def merge_regex_patterns(base_pattern: str, extra_patterns: List[str]) -> str:
    patterns = []
    if base_pattern and str(base_pattern).strip():
        patterns.append(str(base_pattern).strip())
    patterns.extend([p for p in extra_patterns if str(p).strip()])
    return "|".join(patterns)


def compile_regex(pattern: str) -> Optional[re.Pattern]:
    if not pattern or not str(pattern).strip():
        return None
    return re.compile(pattern)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", str(text))


def evaluate_text(text: str, keyword: str, pos_regex: str, neg_regex: str) -> dict:
    text_clean = normalize_text(text)

    keyword = (keyword or "").strip()
    has_keyword = bool(re.search(re.escape(keyword), text_clean)) if keyword else True

    pos_compiled = compile_regex(pos_regex)
    neg_compiled = compile_regex(neg_regex)

    pos_match = bool(pos_compiled.search(text_clean)) if pos_compiled else True
    neg_match = bool(neg_compiled.search(text_clean)) if neg_compiled else False

    recommended = has_keyword and pos_match and (not neg_match)
    review_needed = has_keyword and (not neg_match) and (not pos_match)

    if not has_keyword:
        reason = "키워드없음"
    elif neg_match:
        reason = "부정패턴매칭"
    elif pos_match:
        reason = "긍정패턴매칭"
    else:
        reason = "검토필요"

    return {
        "입력원문": text,
        "정규화문자열": text_clean,
        "has_keyword": has_keyword,
        "pos_match": pos_match,
        "neg_match": neg_match,
        "추천포함": recommended,
        "검토필요": review_needed,
        "판단근거": reason,
    }
