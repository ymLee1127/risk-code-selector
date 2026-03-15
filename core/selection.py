"""선택 결과 저장/불러오기"""
import json
from pathlib import Path
from typing import List

import pandas as pd

from config import settings


def _ensure_data_dir():
    """저장 경로 디렉터리 생성"""
    Path(settings.SAVED_SELECTIONS_PATH).parent.mkdir(parents=True, exist_ok=True)


def load_saved_selection_sets() -> List[dict]:
    path = Path(settings.SAVED_SELECTIONS_PATH)
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def save_saved_selection_sets(items: List[dict]) -> None:
    _ensure_data_dir()
    with open(settings.SAVED_SELECTIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def upsert_selection_set(name: str, description: str, codes: List[str]) -> None:
    items = load_saved_selection_sets()
    now_text = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")

    new_item = {
        "name": name,
        "description": description,
        "codes": list(dict.fromkeys([str(c) for c in codes])),
        "saved_at": now_text,
    }

    replaced = False
    for i, item in enumerate(items):
        if item.get("name") == name:
            items[i] = new_item
            replaced = True
            break

    if not replaced:
        items.append(new_item)

    save_saved_selection_sets(items)


def format_saved_option(item: dict) -> str:
    name = item.get("name", "")
    desc = item.get("description", "")
    count = len(item.get("codes", []))
    saved_at = item.get("saved_at", "")
    return f"{name} | {desc} | {count}건 | {saved_at}"


def build_to_query_string(codes: List[str]) -> str:
    if not codes:
        return "()"
    escaped_codes = [str(code).replace("'", "''") for code in codes]
    inside = ",".join([f"'{code}'" for code in escaped_codes])
    return f"({inside})"
