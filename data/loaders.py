"""데이터 소스 로더 (Excel, CSV, DB)"""
import io
from pathlib import Path
from typing import Optional

import pandas as pd

from config import settings
from db.connection import load_risk_codes_from_db

# 기본 샘플 (엑셀/DB 없을 때 fallback)
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
    """기본 엑셀 파일 또는 샘플 데이터 로드"""
    path = Path(settings.DEFAULT_EXCEL_PATH)
    if path.exists():
        return load_from_excel(str(path), sheet_name=settings.DEFAULT_SHEET_NAME)
    return FALLBACK_SAMPLE.copy()
