import html
import json
import re
import sqlite3
import time
import zipfile
from pathlib import Path

from app.services import error_store


def _now_ms() -> int:
    return int(time.time() * 1000)


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).replace("\r\n", "\n").replace("\r", "\n").strip()


def safe_filename(value: str, fallback: str) -> str:
    text = _clean_text(value) or fallback
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", text)
    text = re.sub(r"\s+", "_", text).strip("._ ")
    return text or fallback


def _anki_field(value: object) -> str:
    text = html.escape(_clean_text(value))
    return text.replace("\n", "<br>")


def _anki_front_text(knowledge_point: str, question: str) -> str:
    kp = _clean_text(knowledge_point)
    q = _clean_text(question) or kp
    normalized_q = re.sub(r"\s+", " ", q).strip().lower()
    normalized_kp = re.sub(r"\s+", " ", kp).strip().lower()
    if normalized_kp and normalized_q in {
        normalized_kp,
        f"review: {normalized_kp}",
        f"review {normalized_kp}",
    }:
        return kp
    if kp and kp.lower() not in q.lower():
        return f"{kp}\n\n{q}"
    return q


def _anki_id(seed: str, index: int) -> int:
    digits = re.sub(r"\D", "", seed or "")
    if digits:
        return int(digits[:12].ljust(12, "0")) + index
    return _now_ms() + index


def knowledge_to_markdown(items: list[dict] | None = None) -> str:
    if items is None:
        items = error_store.get_knowledge_points()

    lines = [
        "# C++rafting Table Knowledge Notes",
        "",
        f"Exported at: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]
    if not items:
        lines.append("_No knowledge notes yet._")
        return "\n".join(lines) + "\n"

    for item in sorted(items, key=lambda kp: kp.get("name", "").lower()):
        name = _clean_text(item.get("name")) or "Untitled Concept"
        source = _clean_text(item.get("source"))
        count = item.get("count", 0)
        description = _clean_text(item.get("description")) or "_No explanation yet._"
        lines.extend([
            f"## {name}",
            "",
            f"- Source: {source or 'Unknown'}",
            f"- Seen: {count}",
            "",
            description,
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"


def review_cards_to_markdown(cards: list[dict] | None = None, deck: str = "") -> str:
    if cards is None:
        cards = error_store.get_errors()

    title = f"C++rafting Table Review Cards"
    if deck:
        title += f" - {deck}"

    lines = [
        f"# {title}",
        "",
        f"Exported at: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]
    if not cards:
        lines.append("_No review cards yet._")
        return "\n".join(lines) + "\n"

    for idx, card in enumerate(cards, start=1):
        kp = _clean_text(card.get("knowledge_point")) or "Uncategorized"
        question = _clean_text(card.get("question")) or "_No question_"
        user_answer = _clean_text(card.get("user_answer"))
        correct = _clean_text(card.get("correct_answer")) or "_No answer_"
        notes = _clean_text(card.get("notes"))
        card_deck = _clean_text(card.get("deck"))
        lines.extend([
            f"## {idx}. {kp}",
            "",
            f"- Deck: {card_deck or 'Uncategorized'}",
            f"- Review count: {card.get('review_count', 0)}",
            f"- Next review: {_clean_text(card.get('next_review')) or 'Unknown'}",
            "",
            "### Question",
            "",
            question,
            "",
        ])
        if user_answer:
            lines.extend(["### Your Answer", "", user_answer, ""])
        lines.extend(["### Correct Answer", "", correct, ""])
        if notes:
            lines.extend(["### Notes", "", notes, ""])
    return "\n".join(lines).rstrip() + "\n"


def write_knowledge_markdown(path: str | Path, items: list[dict] | None = None) -> Path:
    target = Path(path)
    target.write_text(knowledge_to_markdown(items), encoding="utf-8")
    return target


def write_review_markdown(path: str | Path, cards: list[dict] | None = None, deck: str = "") -> Path:
    target = Path(path)
    target.write_text(review_cards_to_markdown(cards, deck), encoding="utf-8")
    return target


def write_review_anki(path: str | Path, cards: list[dict] | None = None,
                      deck_name: str = "C++rafting Table::Review") -> Path:
    if cards is None:
        cards = error_store.get_errors()

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_db = target.with_suffix(".anki2")
    now = int(time.time())
    deck_id = _anki_id(deck_name, 1)
    model_id = _anki_id("cxxrafting-basic-model", 2)

    if tmp_db.exists():
        tmp_db.unlink()
    conn = sqlite3.connect(tmp_db)
    try:
        conn.execute("PRAGMA journal_mode=OFF")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA synchronous=OFF")
        cur = conn.cursor()
        _create_anki_schema(cur)
        _insert_collection(cur, now, deck_id, deck_name, model_id)
        for index, card in enumerate(cards, start=1):
            _insert_anki_card(cur, now, deck_id, model_id, index, card)
        conn.commit()
    finally:
        conn.close()

    try:
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(tmp_db, "collection.anki2")
            zf.writestr("media", "{}")
    finally:
        if tmp_db.exists():
            tmp_db.unlink()
    return target


def _create_anki_schema(cur: sqlite3.Cursor):
    cur.execute(
        "create table col (id integer primary key, crt integer not null, mod integer not null, "
        "scm integer not null, ver integer not null, dty integer not null, usn integer not null, "
        "ls integer not null, conf text not null, models text not null, decks text not null, "
        "dconf text not null, tags text not null)"
    )
    cur.execute(
        "create table notes (id integer primary key, guid text not null, mid integer not null, "
        "mod integer not null, usn integer not null, tags text not null, flds text not null, "
        "sfld text not null, csum integer not null, flags integer not null, data text not null)"
    )
    cur.execute(
        "create table cards (id integer primary key, nid integer not null, did integer not null, "
        "ord integer not null, mod integer not null, usn integer not null, type integer not null, "
        "queue integer not null, due integer not null, ivl integer not null, factor integer not null, "
        "reps integer not null, lapses integer not null, left integer not null, odue integer not null, "
        "odid integer not null, flags integer not null, data text not null)"
    )
    cur.execute("create table revlog (id integer primary key, cid integer not null, usn integer not null, "
                "ease integer not null, ivl integer not null, lastIvl integer not null, factor integer not null, "
                "time integer not null, type integer not null)")
    cur.execute("create table graves (usn integer not null, oid integer not null, type integer not null)")


def _insert_collection(cur: sqlite3.Cursor, now: int, deck_id: int, deck_name: str, model_id: int):
    model = {
        str(model_id): {
            "id": model_id,
            "name": "C++rafting Table Basic",
            "type": 0,
            "mod": now,
            "usn": 0,
            "sortf": 0,
            "did": deck_id,
            "tmpls": [{
                "name": "Card 1",
                "ord": 0,
                "qfmt": "{{Question}}",
                "afmt": "{{FrontSide}}<hr id=answer>{{Answer}}<br><br>{{Notes}}",
                "did": None,
                "bafmt": "",
                "bqfmt": "",
            }],
            "flds": [
                {"name": "Question", "ord": 0, "sticky": False, "rtl": False, "font": "Arial", "size": 20},
                {"name": "Answer", "ord": 1, "sticky": False, "rtl": False, "font": "Arial", "size": 20},
                {"name": "Notes", "ord": 2, "sticky": False, "rtl": False, "font": "Arial", "size": 16},
            ],
            "css": ".card { font-family: arial; font-size: 20px; text-align: left; color: #222; background: #f7f0dc; }",
            "latexPre": "",
            "latexPost": "",
            "req": [[0, "all", [0]]],
            "tags": [],
            "vers": [],
        }
    }
    decks = {
        str(deck_id): {
            "id": deck_id,
            "name": deck_name,
            "desc": "Exported from C++rafting Table",
            "mod": now,
            "usn": 0,
            "lrnToday": [0, 0],
            "revToday": [0, 0],
            "newToday": [0, 0],
            "timeToday": [0, 0],
            "collapsed": False,
            "browserCollapsed": False,
            "dyn": 0,
            "conf": 1,
            "extendNew": 10,
            "extendRev": 50,
        }
    }
    dconf = {
        "1": {
            "id": 1,
            "name": "Default",
            "mod": now,
            "usn": 0,
            "maxTaken": 60,
            "autoplay": True,
            "timer": 0,
            "replayq": True,
            "new": {
                "delays": [1, 10],
                "ints": [1, 4, 7],
                "initialFactor": 2500,
                "separate": True,
                "order": 1,
                "perDay": 20,
            },
            "rev": {
                "perDay": 200,
                "ease4": 1.3,
                "fuzz": 0.05,
                "minSpace": 1,
                "ivlFct": 1,
                "maxIvl": 36500,
                "bury": True,
            },
            "lapse": {
                "delays": [10],
                "mult": 0,
                "minInt": 1,
                "leechFails": 8,
                "leechAction": 0,
            },
        }
    }
    cur.execute(
        "insert into col values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            1, now, now, now, 11, 0, 0, 0, "{}", json.dumps(model),
            json.dumps(decks), json.dumps(dconf), "{}",
        ),
    )


def _insert_anki_card(cur: sqlite3.Cursor, now: int, deck_id: int, model_id: int,
                      index: int, card: dict):
    base = _anki_id(card.get("id", ""), index * 10)
    note_id = base
    card_id = base + 1
    kp = _clean_text(card.get("knowledge_point")) or "Uncategorized"
    question = _clean_text(card.get("question")) or kp
    answer = _clean_text(card.get("correct_answer")) or ""
    notes = _clean_text(card.get("notes"))
    front = _anki_front_text(kp, question)
    fields = "\x1f".join([
        _anki_field(front),
        _anki_field(answer),
        _anki_field(notes),
    ])
    cur.execute(
        "insert into notes values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            note_id, f"cxxrafting-{note_id}", model_id, now, 0, "",
            fields, question[:128], abs(hash(question)) % 1000000000, 0, "",
        ),
    )
    cur.execute(
        "insert into cards values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            card_id, note_id, deck_id, 0, now, 0, 0, 0, index, 0, 2500,
            int(card.get("review_count", 0) or 0), 0, 0, 0, 0, 0, "",
        ),
    )
