from __future__ import annotations

import re
from collections.abc import Mapping


_LABELS = ("A", "B", "C", "D")
_LABEL_PATTERN = re.compile(r"^\s*[\(（]?\s*([A-Da-d])\s*[\)）\.、:：]?\s*$")
_LABELED_TEXT_PATTERN = re.compile(r"^\s*[\(（]?\s*([A-Da-d])\s*[\)）\.、:：]\s*(.+?)\s*$")


def normalize_quiz_question(raw_question: Mapping | None) -> dict:
    """Normalize AI quiz output so UI code can reliably compare answer indexes."""
    question = dict(raw_question or {})
    options = _normalize_options(question.get("options", []))
    answer_raw = _first_present(
        question,
        ("answer", "answer_index", "correct_answer", "correct_option", "correct", "answer_text"),
    )

    answer_idx = _answer_to_index(answer_raw, options)
    if answer_idx is None:
        answer_text = _answer_to_text(answer_raw, options)
        if answer_text:
            answer_idx = _ensure_answer_option(options, answer_text)

    if len(options) > 4:
        if answer_idx is not None and answer_idx >= 4:
            options[3] = options[answer_idx]
            answer_idx = 3
        options = options[:4]

    if answer_idx is None or not (0 <= answer_idx < len(options)):
        answer_idx = -1

    question["options"] = options
    question["answer"] = answer_idx
    return question


def normalize_quiz_questions(raw_questions: object) -> list[dict]:
    if isinstance(raw_questions, dict):
        raw_questions = raw_questions.get("quiz_questions", [raw_questions])
    if not isinstance(raw_questions, list):
        raw_questions = [raw_questions]
    return [
        normalize_quiz_question(item)
        for item in raw_questions
        if isinstance(item, Mapping)
    ]


def _normalize_options(raw_options: object) -> list[str]:
    if not isinstance(raw_options, list):
        return []
    options: list[str] = []
    for raw_option in raw_options:
        option = _strip_option_label(str(raw_option).strip())
        if option:
            options.append(option)
    return options


def _answer_to_index(answer: object, options: list[str]) -> int | None:
    if isinstance(answer, bool):
        return None

    if isinstance(answer, int):
        if 0 <= answer < len(options):
            return answer
        if answer == len(options) and 1 <= answer <= 4:
            return answer - 1
        return None

    if not isinstance(answer, str):
        return None

    text = answer.strip()
    if not text:
        return None

    label_match = _LABEL_PATTERN.match(text)
    if label_match:
        return _LABELS.index(label_match.group(1).upper())

    labeled_text_match = _LABELED_TEXT_PATTERN.match(text)
    if labeled_text_match:
        return _LABELS.index(labeled_text_match.group(1).upper())

    if text.isdigit():
        value = int(text)
        if 0 <= value < len(options):
            return value
        if value == len(options) and 1 <= value <= 4:
            return value - 1

    normalized_answer = _normalize_compare_text(text)
    for index, option in enumerate(options):
        if _normalize_compare_text(option) == normalized_answer:
            return index
    return None


def _answer_to_text(answer: object, options: list[str]) -> str:
    if not isinstance(answer, str):
        return ""
    text = answer.strip()
    if not text or _LABEL_PATTERN.match(text) or text.isdigit():
        return ""

    labeled_text_match = _LABELED_TEXT_PATTERN.match(text)
    if labeled_text_match:
        label_index = _LABELS.index(labeled_text_match.group(1).upper())
        if 0 <= label_index < len(options):
            return options[label_index]
        return _strip_option_label(labeled_text_match.group(2))

    return _strip_option_label(text)


def _ensure_answer_option(options: list[str], answer_text: str) -> int:
    normalized_answer = _normalize_compare_text(answer_text)
    for index, option in enumerate(options):
        if _normalize_compare_text(option) == normalized_answer:
            return index

    if len(options) >= 4:
        options[-1] = answer_text
        return len(options) - 1
    options.append(answer_text)
    return len(options) - 1


def _strip_option_label(text: str) -> str:
    match = _LABELED_TEXT_PATTERN.match(text)
    if match:
        return match.group(2).strip()
    return text.strip()


def _normalize_compare_text(text: str) -> str:
    return re.sub(r"\s+", "", _strip_option_label(text)).strip().lower()


def _first_present(question: dict, keys: tuple[str, ...]) -> object:
    for key in keys:
        if key in question and question[key] not in (None, ""):
            return question[key]
    return None
