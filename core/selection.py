"""선택 결과 저장/불러오기"""
import json
from pathlib import Path
from typing import List

import pandas as pd

from config import settings


def _ensure_data_dir():
    """저장 경로 디렉터리 생성"""
    Path(settings.SAVED_SELECTIONS_PATH).parent.mkdir(parents=True, exist_ok=True)


def load_saved_selection_sets(entity_type: str | None = None) -> List[dict]:
    path = Path(settings.SAVED_SELECTIONS_PATH)
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        if entity_type:
            return [i for i in data if i.get("entity_type", "위험률") == entity_type]
        return data
    except Exception:
        return []


def save_saved_selection_sets(items: List[dict]) -> None:
    _ensure_data_dir()
    with open(settings.SAVED_SELECTIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def upsert_selection_set(
    name: str,
    description: str,
    codes: List[str],
    entity_type: str = "위험률",
) -> None:
    items = load_saved_selection_sets()  # 전체 로드
    now_text = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")

    new_item = {
        "entity_type": entity_type,
        "name": name,
        "description": description,
        "codes": list(dict.fromkeys([str(c) for c in codes])),
        "saved_at": now_text,
    }

    replaced = False
    for i, item in enumerate(items):
        if item.get("entity_type") == entity_type and item.get("name") == name:
            items[i] = new_item
            replaced = True
            break

    if not replaced:
        items.append(new_item)

    save_saved_selection_sets(items)


def find_saved_item(name: str, entity_type: str | None = None) -> dict | None:
    """이름(및 엔티티 타입)으로 저장 항목 찾기"""
    items = load_saved_selection_sets()
    for item in items:
        if item.get("name") != name:
            continue
        if entity_type is None or item.get("entity_type", "위험률") == entity_type:
            return item
    return None


def format_saved_option(item: dict) -> str:
    entity = item.get("entity_type", "위험률")
    name = item.get("name", "")
    desc = item.get("description", "")
    count = len(item.get("codes", []))
    saved_at = item.get("saved_at", "")
    return f"[{entity}] {name} | {desc} | {count}건 | {saved_at}"


def build_to_query_string(codes: List[str]) -> str:
    if not codes:
        return "()"
    escaped_codes = [str(code).replace("'", "''") for code in codes]
    inside = ",".join([f"'{code}'" for code in escaped_codes])
    return f"({inside})"
