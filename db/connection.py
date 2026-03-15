"""DB 연결 및 위험률 코드 조회"""
from typing import Optional

import pandas as pd

from config import settings


def get_connection():
    """SQLAlchemy 엔진 반환 (lazy import)"""
    from sqlalchemy import create_engine

    url = settings.DATABASE_URL
    connect_args = {}
    if "sqlite" in url:
        connect_args["check_same_thread"] = False
    return create_engine(url, connect_args=connect_args)


def test_connection() -> tuple[bool, str]:
    """DB 연결 테스트. (성공여부, 메시지) 반환"""
    try:
        from sqlalchemy import text

        engine = get_connection()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "연결 성공"
    except Exception as e:
        return False, str(e)


def load_risk_codes_from_db(
    table: Optional[str] = None,
    code_col: Optional[str] = None,
    nm_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    DB에서 위험률 코드 마스터 로드.
    반환 DataFrame은 CODE, NM 컬럼을 가짐.
    """
    table = table or settings.DB_RISK_CODE_TABLE
    code_col = code_col or settings.DB_CODE_COLUMN
    nm_col = nm_col or settings.DB_NM_COLUMN

    from sqlalchemy import text

    # 식별자 검증 (SQL injection 방지)
    for name, val in [("table", table), ("code_col", code_col), ("nm_col", nm_col)]:
        if not val.replace("_", "").isalnum():
            raise ValueError(f"잘못된 {name}: {val}")

    engine = get_connection()
    query = text(f'SELECT "{code_col}" AS CODE, "{nm_col}" AS NM FROM "{table}"')
    df = pd.read_sql(query, engine)
    return df
