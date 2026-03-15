"""애플리케이션 설정 (DB, 경로 등)"""
import os
from pathlib import Path

# .env 로드 (있으면)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

# 프로젝트 루트 (config 기준 상위)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 기본 경로
DEFAULT_EXCEL_PATH = str(PROJECT_ROOT / "risk_code_master.xlsx")
DEFAULT_SHEET_NAME = 0
DEFAULT_KEYWORD = "치아파절"

# 저장소 (선택 결과, DB 파일 등)
STORAGE_DIR = PROJECT_ROOT / "storage"
STORAGE_DIR.mkdir(exist_ok=True)
SAVED_SELECTIONS_PATH = str(STORAGE_DIR / "saved_selection_sets.json")

# DB 설정 (환경변수 또는 기본값)
_DEFAULT_DB_PATH = (STORAGE_DIR / "risk_code.db").as_posix()
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{_DEFAULT_DB_PATH}",
)
# PostgreSQL 예: postgresql://user:pass@localhost:5432/dbname
# MySQL 예: mysql+pymysql://user:pass@localhost:3306/dbname

# 위험률 코드 마스터 테이블 (DB 사용 시)
# 테이블에 CODE, NM 컬럼이 있어야 함
DB_RISK_CODE_TABLE = os.getenv("DB_RISK_CODE_TABLE", "risk_code_master")
DB_CODE_COLUMN = os.getenv("DB_CODE_COLUMN", "CODE")
DB_NM_COLUMN = os.getenv("DB_NM_COLUMN", "NM")
