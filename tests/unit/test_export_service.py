import sqlite3
import json


def test_knowledge_markdown_contains_concepts():
    from app.services.export_service import knowledge_to_markdown

    text = knowledge_to_markdown([
        {
            "name": "Pointers",
            "source": "oj",
            "count": 2,
            "description": "Use `*` and `&` carefully.",
        }
    ])

    assert "# C++rafting Table Knowledge Notes" in text
    assert "## Pointers" in text
    assert "Use `*` and `&` carefully." in text


def test_review_markdown_contains_cards():
    from app.services.export_service import review_cards_to_markdown

    text = review_cards_to_markdown([
        {
            "knowledge_point": "Arrays",
            "question": "What is out-of-bounds access?",
            "correct_answer": "Undefined behavior.",
            "deck": "STL",
            "review_count": 1,
        }
    ], deck="STL")

    assert "# C++rafting Table Review Cards - STL" in text
    assert "## 1. Arrays" in text
    assert "Undefined behavior." in text


def test_safe_filename_removes_windows_reserved_characters():
    from app.services.export_service import safe_filename

    assert safe_filename('指针/内存:Deck?', 'review') == '指针_内存_Deck'


def test_anki_front_text_does_not_leak_literal_break_tags():
    from app.services.export_service import _anki_field, _anki_front_text

    front = _anki_front_text("数组", "Review: 数组")
    assert front == "数组"
    assert "<br>" not in front
    assert _anki_field("数组\n\n题目").count("<br>") == 2


def test_review_anki_schema_writes_note_and_card():
    from app.services.export_service import (
        _create_anki_schema,
        _insert_anki_card,
        _insert_collection,
    )

    conn = sqlite3.connect(":memory:")
    try:
        cur = conn.cursor()
        _create_anki_schema(cur)
        _insert_collection(cur, 123456, 1001, "C++rafting Table::Review", 2002)
        _insert_anki_card(cur, 123456, 1001, 2002, 1, {
            "id": "abc123",
            "knowledge_point": "Pointers",
            "question": "What does delete do?",
            "correct_answer": "It releases dynamic storage.",
            "notes": "Check dangling pointers.",
        })
        decks_json = conn.execute("select decks from col").fetchone()[0]
        deck = json.loads(decks_json)["1001"]
        note_count = conn.execute("select count(*) from notes").fetchone()[0]
        card_count = conn.execute("select count(*) from cards").fetchone()[0]
    finally:
        conn.close()

    assert note_count == 1
    assert card_count == 1
    assert deck["newToday"] == [0, 0]
    assert deck["revToday"] == [0, 0]
    assert deck["lrnToday"] == [0, 0]
    assert deck["timeToday"] == [0, 0]
