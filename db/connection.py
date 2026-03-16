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


def load_from_table(table: str, columns: list[str] | None = None) -> pd.DataFrame:
    """
    테이블에서 데이터 로드. columns 미지정 시 * (전체).
    """
    from sqlalchemy import text

    for name, val in [("table", table)]:
        if not val.replace("_", "").isalnum():
            raise ValueError(f"잘못된 {name}: {val}")

    engine = get_connection()
    if columns:
        cols_str = ", ".join(f'"{c}"' for c in columns)
        query = text(f'SELECT {cols_str} FROM "{table}"')
    else:
        query = text(f'SELECT * FROM "{table}"')
    return pd.read_sql(query, engine)


def import_risk_codes_to_db(
    df: pd.DataFrame,
    table: Optional[str] = None,
    mode: str = "replace",
) -> tuple[int, str]:
    """
    DataFrame을 risk_code_master 테이블에 반영.
    df는 CODE, NM 컬럼을 가져야 함.
    mode: "replace" (전체 교체) | "append" (추가, 중복 시 무시)
    반환: (반영된 행 수, 메시지)
    """
    from sqlalchemy import text

    table = table or settings.DB_RISK_CODE_TABLE
    if "CODE" not in df.columns or "NM" not in df.columns:
        raise ValueError("DataFrame에 CODE, NM 컬럼이 필요합니다.")

    engine = get_connection()
    df_clean = df[["CODE", "NM"]].dropna(subset=["CODE"]).astype(str)
    df_clean = df_clean.drop_duplicates(subset=["CODE"], keep="first")

    with engine.connect() as conn:
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS "{table}" (
                CODE VARCHAR(50) PRIMARY KEY,
                NM VARCHAR(500)
            )
        """))
        conn.commit()

        if mode == "replace":
            conn.execute(text(f'DELETE FROM "{table}"'))
            conn.commit()

        inserted = 0
        for _, row in df_clean.iterrows():
            result = conn.execute(
                text(f'INSERT OR IGNORE INTO "{table}" (CODE, NM) VALUES (:code, :nm)'),
                {"code": str(row["CODE"])[:50], "nm": str(row["NM"])[:500]},
            )
            if result.rowcount and result.rowcount > 0:
                inserted += 1
        conn.commit()

    return inserted, f"{inserted}건 반영 완료 (총 {len(df_clean)}건 중)"


def import_entity_to_db(
    entity_type: str,
    df: pd.DataFrame,
    mode: str = "replace",
) -> tuple[int, str]:
    """
    엔티티 타입별 DB 반영.
    위험률: CODE, NM → risk_code_master
    상품: display_cols → product_master
    담보: display_cols → coverage_master
    """
    from config.entity_types import get_entity_config

    config = get_entity_config(entity_type)
    table = config.get("table", "risk_code_master")
    code_col = config["code_col"]
    required_cols = config.get("required_cols", {code_col})

    if entity_type == "위험률":
        if "CODE" not in df.columns or "NM" not in df.columns:
            raise ValueError("위험률은 CODE, NM 컬럼이 필요합니다.")
        return import_risk_codes_to_db(df, table=table, mode=mode)

    # 상품/담보: display_cols 매칭
    display_cols = config.get("display_cols", [])
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"필수 컬럼 누락: {', '.join(sorted(missing))}")

    df_clean = df.copy()
    for col in display_cols:
        if col not in df_clean.columns:
            df_clean[col] = ""
    df_clean = df_clean[[c for c in display_cols if c in df_clean.columns]]
    df_clean = df_clean.dropna(subset=[code_col]).astype(str)
    df_clean = df_clean.drop_duplicates(subset=[code_col], keep="first")

    from sqlalchemy import text

    engine = get_connection()
    cols = list(df_clean.columns)
    cols_str = ", ".join(f'"{c}"' for c in cols)
    placeholders = ", ".join(f":{c}" for c in cols)

    with engine.connect() as conn:
        if mode == "replace":
            conn.execute(text(f'DROP TABLE IF EXISTS "{table}"'))
            conn.commit()

        # 동적 컬럼으로 테이블 생성
        col_defs = ", ".join(f'"{c}" VARCHAR(500)' for c in cols)
        pk_def = f'PRIMARY KEY ("{code_col}")'
        conn.execute(
            text(f'CREATE TABLE IF NOT EXISTS "{table}" ({col_defs}, {pk_def})')
        )
        conn.commit()

        inserted = 0
        for _, row in df_clean.iterrows():
            params = {c: str(row[c])[:500] for c in cols}
            result = conn.execute(
                text(f'INSERT OR IGNORE INTO "{table}" ({cols_str}) VALUES ({placeholders})'),
                params,
            )
            if result.rowcount and result.rowcount > 0:
                inserted += 1
        conn.commit()

    return inserted, f"{inserted}건 반영 완료 (총 {len(df_clean)}건 중)"
