import fitz


def extract_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    lines: list[str] = []
    for page in doc:
        blocks = page.get_text("blocks")
        blocks.sort(key=lambda b: (b[1], b[0]))
        for b in blocks:
            text = b[4].strip()
            if not text:
                continue
            y_ratio = b[1] / page.rect.height
            if y_ratio < 0.05 or y_ratio > 0.93:
                continue
            lines.append(text)
    doc.close()
    return "\n\n".join(lines)
