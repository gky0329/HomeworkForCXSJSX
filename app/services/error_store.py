import json
import threading
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "user"
DATA_DIR.mkdir(parents=True, exist_ok=True)
ERRORS_PATH = DATA_DIR / "errors.json"
KNOWLEDGE_PATH = DATA_DIR / "knowledge.json"
ACTIVITY_PATH = DATA_DIR / "activity.json"

_lock = threading.Lock()


def _load(path: Path) -> list:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(path: Path, data: list):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_error(knowledge_point: str, question: str,
              user_answer: str, correct_answer: str, context: str = ""):
    with _lock:
        errors = _load(ERRORS_PATH)
        entry = {
            "id": uuid.uuid4().hex,
            "knowledge_point": knowledge_point,
            "question": question,
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "context": context,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reviewed": False,
            "review_count": 0,
        }
        errors.insert(0, entry)
        _save(ERRORS_PATH, errors)


def get_errors(reviewed: Optional[bool] = None) -> list:
    errors = _load(ERRORS_PATH)
    if reviewed is not None:
        errors = [e for e in errors if e.get("reviewed", False) == reviewed]
    return sorted(errors, key=lambda e: e.get("timestamp", ""), reverse=True)


def get_error_frequency() -> dict[str, int]:
    errors = get_errors()
    freq: dict[str, int] = {}
    for e in errors:
        kp = e.get("knowledge_point", "unknown")
        freq[kp] = freq.get(kp, 0) + 1
    return freq


def mark_reviewed(error_id: str):
    with _lock:
        errors = _load(ERRORS_PATH)
        for e in errors:
            if e.get("id") == error_id:
                e["reviewed"] = True
                e["review_count"] = e.get("review_count", 0) + 1
                _save(ERRORS_PATH, errors)
                return


def delete_error(error_id: str):
    with _lock:
        errors = _load(ERRORS_PATH)
        errors[:] = [e for e in errors if e.get("id") != error_id]
        _save(ERRORS_PATH, errors)


def add_knowledge_point(name: str, source: str = ""):
    with _lock:
        kps = _load(KNOWLEDGE_PATH)
        for kp in kps:
            if kp["name"] == name:
                kp["count"] = kp.get("count", 1) + 1
                _save(KNOWLEDGE_PATH, kps)
                return
        kps.append({
            "name": name,
            "source": source,
            "count": 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        _save(KNOWLEDGE_PATH, kps)


def get_knowledge_points() -> list:
    return _load(KNOWLEDGE_PATH)


def get_all_stats() -> dict:
    errors = get_errors()
    freq = get_error_frequency()
    kps = get_knowledge_points()
    return {
        "total_errors": len(errors),
        "unreviewed": len([e for e in errors if not e.get("reviewed", False)]),
        "error_frequency": freq,
        "knowledge_points": len(kps),
    }


def log_activity(action: str, detail: str = ""):
    with _lock:
        items = _load(ACTIVITY_PATH)
        items.insert(0, {
            "action": action,
            "detail": detail,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        if len(items) > 50:
            items = items[:50]
        _save(ACTIVITY_PATH, items)


def get_recent_activity(limit: int = 8) -> list:
    items = _load(ACTIVITY_PATH)
    return items[:limit]
