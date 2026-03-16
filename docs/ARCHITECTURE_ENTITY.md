# 위험률·상품·담보 통합 선택기 아키텍처

## 1. 엔티티 타입별 특성

| 구분 | 위험률 | 상품 | 담보 |
|------|--------|------|------|
| **검색 방식** | NM 기반 정규식 | 상품명 + 파라미터 조합 | 보험명 + 파라미터 조합 |
| **코드 컬럼** | CODE | 상품코드 | 보험코드(추정) |
| **이름 컬럼** | NM | 상품명 | 보험명 |

### 상품 컬럼
- 외부번호, 상품코드, 파라미터보험기간, 파라미터납입주기, 이전상품코드
- 상품명, 약식용도상품명, 생성일, 변경일

### 담보 컬럼 (상품 + 추가)
- 상품과 동일 + **보험명**, **이전보험코드** 등

---

## 2. 제안 구조

```
risk-code-selector/
├── config/
│   ├── settings.py
│   └── entity_types.py      # NEW: 엔티티 타입별 설정
├── core/
│   ├── regex_utils.py       # 위험률용 (기존)
│   ├── filter.py            # 공통 필터 (확장)
│   ├── filter_risk.py       # 위험률 전용 (NM 정규식)
│   ├── filter_product.py    # 상품 전용 (이름+파라미터)
│   └── filter_coverage.py   # 담보 전용
├── app/
│   ├── streamlit_app.py     # 엔티티 타입 선택 후 공통 UI
│   └── components/          # NEW: 재사용 컴포넌트
│       ├── selector_risk.py
│       ├── selector_product.py
│       └── selector_coverage.py
├── pages/
│   ├── 1_selector.py        # 통합 선택기 (위험률/상품/담보 탭)
│   ├── 2_saved_results.py
│   └── 3_excel_to_db.py
└── data/
    └── loaders.py           # 엔티티별 로더 확장
```

---

## 3. 엔티티 타입 설정 (config/entity_types.py)

```python
ENTITY_TYPES = {
    "위험률": {
        "code_col": "CODE",
        "name_col": "NM",
        "search_mode": "regex",           # NM 정규식
        "search_cols": ["NM"],
        "display_cols": ["CODE", "NM"],
        "table": "risk_code_master",
        "excel_path": "risk_code_master.xlsx",
    },
    "상품": {
        "code_col": "상품코드",
        "name_col": "상품명",
        "search_mode": "keyword_combo",   # 이름 + 파라미터 조합
        "search_cols": ["상품명", "파라미터보험기간", "파라미터납입주기", "상품코드", "외부번호"],
        "param_cols": ["파라미터보험기간", "파라미터납입주기"],  # 필터용
        "display_cols": ["외부번호", "상품코드", "파라미터보험기간", "파라미터납입주기", 
                        "이전상품코드", "상품명", "약식용도상품명", "생성일", "변경일"],
        "table": "product_master",
        "excel_path": "product_master.xlsx",
    },
    "담보": {
        "code_col": "보험코드",
        "name_col": "보험명",
        "search_mode": "keyword_combo",
        "search_cols": ["보험명", "파라미터보험기간", "파라미터납입주기", "보험코드", "이전보험코드"],
        "param_cols": ["파라미터보험기간", "파라미터납입주기"],
        "display_cols": ["보험코드", "보험명", "이전보험코드", "파라미터보험기간", 
                        "파라미터납입주기", "상품코드", ...],
        "table": "coverage_master",
        "excel_path": "coverage_master.xlsx",
    },
}
```

---

## 4. 검색 로직 차이

### 위험률 (기존)
- **키워드** → NM에 포함 여부
- **긍정/부정 정규식** → NM 매칭
- 추천/검토/부정 패턴 판단

### 상품·담보 (신규)
- **이름 검색**: 상품명/보험명에 키워드 포함 (LIKE 또는 contains)
- **파라미터 필터**: 파라미터보험기간, 파라미터납입주기 등 정확/부분 매칭
- 예: `상품명 LIKE '%치아%' AND 파라미터보험기간 = '10' AND 파라미터납입주기 = '월납'`

**UI 예시 (상품/담보)**:
```
[상품명 검색] _______________
[파라미터보험기간] [전체 ▼] 또는 [직접입력]
[파라미터납입주기] [전체 ▼] 또는 [직접입력]
[추가 검색어] _______________  (다른 컬럼 검색)
```

---

## 5. 구현 단계 제안

### Phase 1: 설정 분리
- `config/entity_types.py` 생성
- 기존 위험률 로직을 entity_config 기반으로 리팩터

### Phase 2: 통합 선택기 UI
- 상단에 **위험률 | 상품 | 담보** 탭 또는 라디오
- 선택한 엔티티에 따라 사이드바/필터 UI 변경

### Phase 3: 상품·담보 필터
- `filter_product.py`, `filter_coverage.py` 구현
- 이름 + 파라미터 조합 검색

### Phase 4: 데이터 소스
- 상품/담보용 Excel 경로, DB 테이블 추가
- `loaders.py`에 엔티티별 로드 함수 추가

---

## 6. 저장 구조 확장

선택 결과 저장 시 엔티티 타입 구분:

```json
{
  "entity_type": "위험률",
  "name": "치아파절_1차",
  "codes": ["K123", "K345"],
  "saved_at": "..."
}
```

또는 파일 분리: `saved_risk.json`, `saved_product.json`, `saved_coverage.json`
