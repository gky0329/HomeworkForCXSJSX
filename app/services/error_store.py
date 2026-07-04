import json
import logging
import os
import threading
import uuid
import math
from pathlib import Path
from datetime import datetime, timezone, timedelta

_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "user"
ERRORS_PATH = _DATA_DIR / "errors.json"
KNOWLEDGE_PATH = _DATA_DIR / "knowledge.json"
ACTIVITY_PATH = _DATA_DIR / "activity.json"
SCORES_PATH = _DATA_DIR / "scores.json"
DEPS_PATH = _DATA_DIR / "dependencies.json"

_lock = threading.RLock()
logger = logging.getLogger(__name__)


def _ensure_data_dir():
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        import tempfile
        _fallback = Path(tempfile.gettempdir()) / "cxx_visualizer"
        _fallback.mkdir(parents=True, exist_ok=True)
        global ERRORS_PATH, KNOWLEDGE_PATH, ACTIVITY_PATH, SCORES_PATH, DEPS_PATH
        ERRORS_PATH = _fallback / "errors.json"
        KNOWLEDGE_PATH = _fallback / "knowledge.json"
        ACTIVITY_PATH = _fallback / "activity.json"
        SCORES_PATH = _fallback / "scores.json"
        DEPS_PATH = _fallback / "dependencies.json"


def _load(path: Path) -> list:
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load %s: %s", path, e)
        return []


def _save(path: Path, data: list):
    _ensure_data_dir()
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    try:
        os.replace(tmp_path, path)
    except OSError:
        tmp_path.unlink(missing_ok=True)
        raise


_DECK_KEYWORDS = {
    "指针与内存": ["指针", "堆", "内存", "new", "delete", "smart", "引用", "地址", "malloc", "free"],
    "面向对象": ["构造", "析构", "class", "继承", "多态", "虚函数", "vtable", "lambda", "函数对象", "模板"],
    "STL容器": ["vector", "map", "set", "list", "queue", "stack", "deque", "string", "pair", "iterator", "容器", "数组"],
    "基础语法": ["变量", "类型", "int", "输入", "输出", "运算符", "循环", "条件", "函数", "定义", "声明", "初始化", "iostream", "cin", "cout", "基本", "算术"],
}

def suggest_deck(name: str) -> str:
    low = name.lower()
    for deck, keywords in _DECK_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in low:
                return deck
    return "其他"


def add_error(knowledge_point: str, question: str,
              user_answer: str, correct_answer: str, context: str = "",
              deck: str = ""):
    with _lock:
        errors = _load(ERRORS_PATH)
        now = datetime.now(timezone.utc)
        entry = {
            "id": uuid.uuid4().hex,
            "knowledge_point": knowledge_point,
            "question": question,
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "context": context,
            "deck": deck,
            "timestamp": now.isoformat(),
            "reviewed": False,
            "review_count": 0,
            "n": 0,
            "ef": 2.5,
            "interval": 1,
            "next_review": now.isoformat(),
            "notes": "",
        }
        errors.insert(0, entry)
        _save(ERRORS_PATH, errors)


def get_errors(reviewed: bool | None = None) -> list:
    with _lock:
        errors = _load(ERRORS_PATH)
        if reviewed is not None:
            errors = [e for e in errors if e.get("reviewed", False) == reviewed]
        return sorted(errors, key=lambda e: e.get("timestamp", ""), reverse=True)


def get_error_frequency() -> dict[str, int]:
    with _lock:
        errors = _load(ERRORS_PATH)
        freq: dict[str, int] = {}
        for e in errors:
            kp = e.get("knowledge_point", "unknown")
            freq[kp] = freq.get(kp, 0) + 1
        return freq


def get_due_cards() -> list:
    now = datetime.now(timezone.utc).isoformat()
    with _lock:
        errors = _load(ERRORS_PATH)
        return [e for e in errors
                if e.get("next_review", "") <= now]


def get_due_cards_by_deck(deck: str) -> list:
    now = datetime.now(timezone.utc).isoformat()
    with _lock:
        errors = _load(ERRORS_PATH)
        return [e for e in errors
                if e.get("next_review", "") <= now
                and e.get("deck", "") == deck]


def get_decks() -> list[str]:
    with _lock:
        errors = _load(ERRORS_PATH)
        decks = sorted(set(e.get("deck", "") for e in errors if e.get("deck")))
        return decks


def update_deck(error_id: str, deck: str):
    with _lock:
        errors = _load(ERRORS_PATH)
        for e in errors:
            if e.get("id") == error_id:
                e["deck"] = deck
                _save(ERRORS_PATH, errors)
                return


def get_uncategorized_cards() -> list:
    with _lock:
        errors = _load(ERRORS_PATH)
        return [e for e in errors if not e.get("deck")]


def schedule_review(error_id: str, quality: int):
    with _lock:
        errors = _load(ERRORS_PATH)
        for e in errors:
            if e.get("id") != error_id:
                continue
            n = e.get("n", 0)
            ef = e.get("ef", 2.5)
            interval = e.get("interval", 1)

            if quality >= 3:
                if n == 0:
                    interval = 1
                elif n == 1:
                    interval = 6
                else:
                    interval = round(interval * ef)
                n += 1
            else:
                if n == 0:
                    interval = 0
                else:
                    n = 0
                    interval = 1

            ef = ef + (0.1 - (3 - quality) * (0.08 + (3 - quality) * 0.02))
            ef = max(1.3, ef)

            if interval == 0:
                days = datetime.now(timezone.utc)
            else:
                days = datetime.now(timezone.utc) + timedelta(days=max(1, interval))

            e["n"] = n
            e["ef"] = ef
            e["interval"] = interval
            e["next_review"] = days.isoformat()
            e["reviewed"] = True
            e["review_count"] = e.get("review_count", 0) + 1
            _save(ERRORS_PATH, errors)
            return


def update_notes(error_id: str, notes: str):
    with _lock:
        errors = _load(ERRORS_PATH)
        for e in errors:
            if e.get("id") == error_id:
                e["notes"] = notes
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
            "description": "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        _save(KNOWLEDGE_PATH, kps)


def delete_knowledge_point(name: str):
    with _lock:
        kps = _load(KNOWLEDGE_PATH)
        kps[:] = [kp for kp in kps if kp["name"] != name]
        _save(KNOWLEDGE_PATH, kps)


def set_knowledge_description(name: str, description: str):
    with _lock:
        kps = _load(KNOWLEDGE_PATH)
        for kp in kps:
            if kp["name"] == name:
                kp["description"] = description
                _save(KNOWLEDGE_PATH, kps)
                return


def get_knowledge_points() -> list:
    with _lock:
        return _load(KNOWLEDGE_PATH)


def get_all_stats() -> dict:
    with _lock:
        errors = _load(ERRORS_PATH)
        unreviewed = len([e for e in errors if not e.get("reviewed", False)])
        freq: dict[str, int] = {}
        for e in errors:
            kp = e.get("knowledge_point", "unknown")
            freq[kp] = freq.get(kp, 0) + 1
        kps = _load(KNOWLEDGE_PATH)
        return {
            "total_errors": len(errors),
            "unreviewed": unreviewed,
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
    with _lock:
        items = _load(ACTIVITY_PATH)
        return items[:limit]


def record_review_result(kp_name: str, correct: bool):
    with _lock:
        scores = _load(SCORES_PATH)
        for s in scores:
            if s["name"] == kp_name:
                s["reviews"] = s.get("reviews", 0) + 1
                if correct:
                    s["correct"] = s.get("correct", 0) + 1
                else:
                    s["wrong"] = s.get("wrong", 0) + 1
                s["last_reviewed"] = datetime.now(timezone.utc).isoformat()
                _save(SCORES_PATH, scores)
                return
        scores.append({
            "name": kp_name,
            "reviews": 1,
            "correct": 1 if correct else 0,
            "wrong": 0 if correct else 1,
            "last_reviewed": datetime.now(timezone.utc).isoformat(),
        })
        _save(SCORES_PATH, scores)


def get_ucb_queue(c: float = 1.0) -> list[dict]:
    with _lock:
        scores = _load(SCORES_PATH)
        if not scores:
            return []

        total_reviews = sum(s.get("reviews", 0) for s in scores)

        result = []
        for s in scores:
            correct = s.get("correct", 0)
            wrong = s.get("wrong", 0)
            reviews = s.get("reviews", 0)
            win_rate = (correct + 0.5) / (correct + wrong + 1.0)
            exploration = c * math.sqrt(
                math.log(total_reviews + 1) / max(reviews, 1)
            )
            ucb = win_rate + exploration
            result.append({
                "name": s["name"],
                "correct": correct,
                "wrong": wrong,
                "reviews": reviews,
                "win_rate": round(win_rate, 2),
                "ucb": round(ucb, 4),
                "last_reviewed": s.get("last_reviewed", ""),
            })

        result.sort(key=lambda x: -x["ucb"])
        return result


def set_dependency(parent: str, child: str):
    with _lock:
        deps = _load(DEPS_PATH)
        for d in deps:
            if d["parent"] == parent and d["child"] == child:
                return
        deps.append({"parent": parent, "child": child})
        _save(DEPS_PATH, deps)


def get_dependencies(name: str) -> list[str]:
    with _lock:
        deps = _load(DEPS_PATH)
        return sorted(set(
            d["child"] for d in deps if d["parent"] == name
        ))
