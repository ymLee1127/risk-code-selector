"""데이터 소스 로더 (Excel, CSV, DB)"""
import io
from pathlib import Path
from typing import Optional

import pandas as pd

from config import settings
from config.entity_types import get_entity_config
from db.connection import load_from_table, load_risk_codes_from_db

# 위험률 기본 샘플
FALLBACK_SAMPLE = pd.DataFrame({
    "CODE": ["K123", "K345", "K66", "K990", "K87", "K999"],
    "NM": [
        "무)치아파절발생율",
        "무)예정재해골절발생율_치아파절제외",
        "예정재해골절-치아파절아님",
        "재해골절발생율-치아파절포함_사용x",
        "발생율-치아파절은포함",
        "치아파절포함(치조골제외)",
    ],
})

# 상품 기본 샘플
FALLBACK_PRODUCT = pd.DataFrame({
    "외부번호": ["P001", "P002", "P003"],
    "상품코드RD": ["PRD-A", "PRD-B", "PRD-C"],
    "파라미터보험기간": ["10", "20", "10"],
    "파라미터납입주기": ["월납", "년납", "월납"],
    "이전상품코드": ["", "PRD-A", ""],
    "상품명": ["치아보험A", "종신보험B", "치아보험C"],
    "약식용도상품명": ["치아A", "종신B", "치아C"],
    "생성일": ["2024-01-01", "2024-01-02", "2024-01-03"],
    "변경일": ["2024-01-01", "2024-01-02", "2024-01-03"],
})

# 담보 기본 샘플 (display_cols 구조)
FALLBACK_COVERAGE = pd.DataFrame({
    "CI": ["", "", ""],
    "외부번호": ["P001", "P002", "P001"],
    "담보코드RD": ["CVG-1", "CVG-2", "CVG-3"],
    "보험버전코드": ["", "", ""],
    "이전보험코드": ["", "CVG-1", ""],
    "이전버전코드": ["", "", ""],
    "파라미터보험기간코드": ["10", "20", "10"],
    "파라미터납입주기코드": ["월납", "년납", "월납"],
    "파라미터주피보험자건강상태코드": ["건강", "건강", "건강"],
    "파라미터계약관점피보험자유형코드": ["", "", ""],
    "파라미터자녀일련번호코드": ["", "", ""],
    "파라미터전환구분코드": ["", "", ""],
    "파라미터단체개벌전환구분코드": ["", "", ""],
    "파라미터담보종목코드": ["", "", ""],
    "파라미터갱신최대연령코드": ["", "", ""],
    "파라미터보험유형코드": ["종신", "정기", "종신"],
    "파라미터개인가족구분코드": ["", "", ""],
    "파라미터고액구분코드": ["", "", ""],
    "파라미터보험구분코드": ["", "", ""],
    "파라미터표준이율코드": ["", "", ""],
    "파라미터표준해약공제여부": ["", "", ""],
    "파라미터이전보험코드": ["", "", ""],
    "파라미터이전버전코드": ["", "", ""],
    "파라미터채널구분코드": ["", "", ""],
    "보험명": ["치아담보1", "사망담보2", "치아담보3"],
    "약식용도보험명": ["치아1", "사망2", "치아3"],
    "증권용도보험명": ["", "", ""],
    "템플릿ID": ["", "", ""],
    "생성자": ["", "", ""],
    "생성일": ["2024-01-01", "2024-01-02", "2024-01-03"],
    "생성시간": ["", "", ""],
    "변경자": ["", "", ""],
    "변경일": ["2024-01-01", "2024-01-02", "2024-01-03"],
    "변경시간": ["", "", ""],
    "삭제여부": ["", "", ""],
})


def load_from_excel(
    path: str,
    sheet_name: int | str = 0,
) -> pd.DataFrame:
    """엑셀 파일에서 로드"""
    return pd.read_excel(path, sheet_name=sheet_name)


def load_from_uploaded_file(file_name: str, file_bytes: bytes) -> pd.DataFrame:
    """업로드된 CSV/Excel에서 로드"""
    buffer = io.BytesIO(file_bytes)
    lower = file_name.lower()

    if lower.endswith(".csv"):
        return pd.read_csv(buffer)
    if lower.endswith(".xlsx"):
        return pd.read_excel(buffer)
    raise ValueError("지원하지 않는 파일 형식입니다. CSV 또는 XLSX를 사용하세요.")


def load_from_db(
    table: Optional[str] = None,
    code_col: Optional[str] = None,
    nm_col: Optional[str] = None,
) -> pd.DataFrame:
    """DB에서 위험률 코드 마스터 로드"""
    return load_risk_codes_from_db(table=table, code_col=code_col, nm_col=nm_col)


def load_default_data() -> pd.DataFrame:
    """기본 엑셀 파일 또는 샘플 데이터 로드 (위험률)"""
    path = Path(settings.DEFAULT_EXCEL_PATH)
    if path.exists():
        return load_from_excel(str(path), sheet_name=settings.DEFAULT_SHEET_NAME)
    return FALLBACK_SAMPLE.copy()


def load_by_entity(entity_type: str, source: str = "default", **kwargs) -> pd.DataFrame:
    """
    엔티티 타입별 데이터 로드.
    source: "default" | "upload" | "db"
    """
    config = get_entity_config(entity_type)
    excel_path = config.get("excel_path", "")
    table = config.get("table", "")

    if source == "upload":
        file_name = kwargs.get("file_name", "")
        file_bytes = kwargs.get("file_bytes", b"")
        if not file_bytes:
            raise ValueError("업로드 파일이 없습니다.")
        df = load_from_uploaded_file(file_name, file_bytes)
        return df

    if source == "db":
        try:
            table_override = kwargs.get("table")
            tbl = table_override if table_override else table
            display_cols = config.get("display_cols", [])
            df = load_from_table(tbl, columns=None)
            aliases = config.get("db_column_aliases", {})
            for old_name, new_name in aliases.items():
                if old_name in df.columns and new_name not in df.columns:
                    df = df.rename(columns={old_name: new_name})
            return df
        except Exception:
            return _get_fallback(entity_type)

    # default: excel or fallback
    path = Path(excel_path)
    if path.exists():
        return load_from_excel(str(path), sheet_name=kwargs.get("sheet_name", 0))
    return _get_fallback(entity_type)


def _get_fallback(entity_type: str) -> pd.DataFrame:
    if entity_type == "위험률":
        return FALLBACK_SAMPLE.copy()
    if entity_type == "상품":
        return FALLBACK_PRODUCT.copy()
    if entity_type == "담보":
        return FALLBACK_COVERAGE.copy()
    return FALLBACK_SAMPLE.copy()
