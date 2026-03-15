"""
SQLite DB 초기화 스크립트 (샘플 테이블 생성)

실행: python -m scripts.init_db
"""
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text

from config import settings


def init_db():
    """risk_code_master 테이블 생성 및 샘플 데이터 삽입"""
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    )

    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS risk_code_master (
                CODE VARCHAR(50) PRIMARY KEY,
                NM VARCHAR(500)
            )
        """))
        conn.commit()

        # 샘플 데이터 (이미 있으면 스킵)
        result = conn.execute(text("SELECT COUNT(*) FROM risk_code_master"))
        if result.scalar() == 0:
            conn.execute(text("""
                INSERT INTO risk_code_master (CODE, NM) VALUES
                ('K123', '무)치아파절발생율'),
                ('K345', '무)예정재해골절발생율_치아파절제외'),
                ('K66', '예정재해골절-치아파절아님'),
                ('K990', '재해골절발생율-치아파절포함_사용x'),
                ('K87', '발생율-치아파절은포함'),
                ('K999', '치아파절포함(치조골제외)')
            """))
            conn.commit()
            print("샘플 데이터 삽입 완료")

    print(f"DB 초기화 완료: {settings.DATABASE_URL}")


if __name__ == "__main__":
    init_db()
