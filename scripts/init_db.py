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
from config.entity_types import ENTITY_TYPES


def init_db():
    """risk_code_master, product_master, coverage_master 테이블 생성 및 샘플 데이터 삽입"""
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
            print("위험률 샘플 데이터 삽입 완료")

        # 상품
        prod_cols = ENTITY_TYPES["상품"]["display_cols"]
        prod_defs = ", ".join(f'"{c}" VARCHAR(500)' for c in prod_cols)
        conn.execute(text(f'''
            CREATE TABLE IF NOT EXISTS product_master (
                {prod_defs},
                PRIMARY KEY ("상품코드")
            )
        '''))
        conn.commit()
        result = conn.execute(text("SELECT COUNT(*) FROM product_master"))
        if result.scalar() == 0:
            conn.execute(text("""
                INSERT INTO product_master (
                    외부번호, 상품코드, 파라미터보험기간, 파라미터납입주기, 이전상품코드,
                    상품명, 약식용도상품명, 생성일, 변경일
                ) VALUES
                ('P001', 'PRD-A', '10', '월납', '', '치아보험A', '치아A', '2024-01-01', '2024-01-01'),
                ('P002', 'PRD-B', '20', '년납', 'PRD-A', '종신보험B', '종신B', '2024-01-02', '2024-01-02'),
                ('P003', 'PRD-C', '10', '월납', '', '치아보험C', '치아C', '2024-01-03', '2024-01-03')
            """))
            conn.commit()
            print("상품 샘플 데이터 삽입 완료")

        # 담보
        cov_cols = ENTITY_TYPES["담보"]["display_cols"]
        cov_defs = ", ".join(f'"{c}" VARCHAR(500)' for c in cov_cols)
        cov_code = ENTITY_TYPES["담보"]["code_col"]
        conn.execute(text(f'''
            CREATE TABLE IF NOT EXISTS coverage_master (
                {cov_defs},
                PRIMARY KEY ("{cov_code}")
            )
        '''))
        conn.commit()
        result = conn.execute(text("SELECT COUNT(*) FROM coverage_master"))
        if result.scalar() == 0:
            conn.execute(text("""
                INSERT INTO coverage_master (
                    CI, 외부번호, 담보코드RD, 보험버전코드, 이전보험코드, 이전버전코드,
                    파라미터보험기간코드, 파라미터납입주기코드, 파라미터주피보험자건강상태코드,
                    파라미터계약관점피보험자유형코드, 파라미터자녀일련번호코드, 파라미터전환구분코드,
                    파라미터단체개벌전환구분코드, 파라미터담보종목코드, 파라미터갱신최대연령코드,
                    파라미터보험유형코드, 파라미터개인가족구분코드, 파라미터고액구분코드,
                    파라미터보험구분코드, 파라미터표준이율코드, 파라미터표준해약공제여부,
                    파라미터이전보험코드, 파라미터이전버전코드, 파라미터채널구분코드,
                    보험명, 약식용도보험명, 증권용도보험명, 템플릿ID, 생성자, 생성일, 생성시간,
                    변경자, 변경일, 변경시간, 삭제여부
                ) VALUES
                ('', 'P001', 'CVG-1', '', '', '', '10', '월납', '건강', '', '', '', '', '', '', '종신', '', '', '', '', '', '', '', '', '치아담보1', '치아1', '', '', '', '2024-01-01', '', '', '2024-01-01', '', ''),
                ('', 'P002', 'CVG-2', '', 'CVG-1', '', '20', '년납', '건강', '', '', '', '', '', '', '정기', '', '', '', '', '', '', '', '', '사망담보2', '사망2', '', '', '', '2024-01-02', '', '', '2024-01-02', '', ''),
                ('', 'P001', 'CVG-3', '', '', '', '10', '월납', '건강', '', '', '', '', '', '', '종신', '', '', '', '', '', '', '', '', '치아담보3', '치아3', '', '', '', '2024-01-03', '', '', '2024-01-03', '', '')
            """))
            conn.commit()
            print("담보 샘플 데이터 삽입 완료")

    print(f"DB 초기화 완료: {settings.DATABASE_URL}")


if __name__ == "__main__":
    init_db()
