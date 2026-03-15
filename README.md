# 위험률 코드 선택기 (Risk Code Selector)

정규식 기반 1차 필터와 체크박스 검토를 통해 위험률 코드를 선택하고, 결과를 저장·불러올 수 있는 Streamlit 웹 앱입니다.

## 주요 기능

- **키워드 필터**: 키워드 입력 시 긍정/부정 정규식 자동 생성
- **추가 패턴**: 여러 줄로 긍정/부정 예외 패턴 확장
- **패턴 테스트**: 팝업에서 문구 검증
- **페이지 검토**: 체크박스로 최종 선택 조정
- **결과 저장**: 이름·설명과 함께 선택 결과 저장 및 불러오기
- **to_query**: SQL IN 조건용 문자열 변환
- **CSV 다운로드**: 최종 선택 결과 내보내기

## 페이지 구성

| 페이지 | 설명 |
|--------|------|
| **코드 선택기** (홈) | 키워드 필터, 후보 목록, 최종 선택 |
| **저장 결과 목록** | 저장된 선택 세트 조회, 이름·메모 검색, 코드 선택기로 이동 |
| **엑셀 → DB Import** | 엑셀/텍스트 붙여넣기로 DB 일괄 반영 |

## 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. DB 초기화 (DB 소스 사용 시)

```bash
python -m scripts.init_db
```

### 3. 앱 실행

```bash
streamlit run run.py
```

브라우저에서 `http://localhost:8501` 접속

## 데이터 소스

| 소스 | 설명 |
|------|------|
| **기본 엑셀** | `risk_code_master.xlsx` (프로젝트 루트) |
| **파일 업로드** | CSV 또는 Excel |
| **DB 연결** | SQLite (`storage/risk_code.db`) 또는 `DATABASE_URL` |

DB 테이블은 `CODE`, `NM` 컬럼을 가져야 합니다.

## 프로젝트 구조

```
risk-code-selector/
├── app/                 # Streamlit 메인 앱
│   └── streamlit_app.py
├── config/              # 설정
│   └── settings.py
├── core/                # 비즈니스 로직
│   ├── regex_utils.py   # 정규식 유틸
│   ├── filter.py       # 필터링
│   └── selection.py    # 선택 저장/불러오기
├── data/                # 데이터 로더
│   └── loaders.py
├── db/                  # DB 연결
│   └── connection.py
├── pages/               # 추가 페이지
│   ├── 1_saved_results.py   # 저장 결과 목록
│   └── 2_excel_to_db.py     # 엑셀 → DB Import
├── scripts/
│   └── init_db.py      # DB 초기화
├── storage/             # 저장소 (자동 생성)
│   ├── risk_code.db
│   └── saved_selection_sets.json
├── .env.example
├── requirements.txt
└── run.py
```

## 환경 변수 (.env)

```env
# DB 연결 (선택)
# DATABASE_URL=sqlite:///storage/risk_code.db
# DATABASE_URL=postgresql://user:pass@localhost:5432/dbname

# DB 테이블/컬럼
# DB_RISK_CODE_TABLE=risk_code_master
# DB_CODE_COLUMN=CODE
# DB_NM_COLUMN=NM
```

## 사용 흐름

1. 키워드 입력 → 기본 긍정/부정 패턴 자동 생성
2. 추가 패턴 입력 (한 줄에 하나씩)
3. **패턴 테스트**로 문구 검증
4. 상단 필터로 추천/부정/최종선택만 보기
5. 페이지를 넘기며 체크박스로 최종 조정
6. CSV 다운로드 또는 `to_query` 문자열 변환
7. 선택 결과를 이름·설명과 함께 저장

## 엑셀 → DB Import

- **텍스트 붙여넣기**: 엑셀에서 복사(Ctrl+C) 후 붙여넣기 (DRM 우회)
- **파일 업로드**: xlsx 업로드
- 탭/쉼표 구분 지원, 반영 방식(replace/append) 선택 가능
