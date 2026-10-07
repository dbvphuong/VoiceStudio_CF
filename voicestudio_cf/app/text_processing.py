"""TXT decoding and sentence-aware chunking for VoiceStudio_CF."""

from __future__ import annotations

import re
from pathlib import Path


class TextReadError(ValueError):
    pass


_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?…。！？])\s+")
_SOFT_BOUNDARY = re.compile(r"(?<=[,;:，；：])\s+")


def read_text_file(path: Path) -> str:
    """Đọc file văn bản với tự động nhận diện encoding linh hoạt."""
    raw = path.read_bytes()
    if not raw:
        return ""

    encodings = ["utf-8-sig"]
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        encodings.insert(0, "utf-16")
    # CP1258 cho tiếng Việt Windows cũ, CP1252 cho Latin
    encodings.extend(["utf-8", "cp1258", "cp1252"])

    for encoding in encodings:
        try:
            text = raw.decode(encoding)
            if "\x00" not in text:
                return text.replace("\r\n", "\n").replace("\r", "\n")
        except UnicodeDecodeError:
            continue
    raise TextReadError(
        "Không thể đọc file. Hãy lưu file ở định dạng UTF-8 hoặc UTF-16."
    )


def split_text(text: str, max_chars: int = 700) -> list[str]:
    """Tách văn bản thành các đoạn đọc có ngữ nghĩa hoàn chỉnh không vượt quá max_chars."""
    if max_chars < 100:
        raise ValueError("max_chars phải từ 100 trở lên")
    cleaned = re.sub(r"[ \t]+", " ", text.strip())
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    if not cleaned:
        return []

    chunks: list[str] = []
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", cleaned)]
    for paragraph in paragraphs:
        if not paragraph:
            continue
        _append_units(chunks, paragraph, max_chars, _SENTENCE_BOUNDARY)
    return chunks


def _append_units(
    chunks: list[str], text: str, max_chars: int, boundary: re.Pattern[str]
) -> None:
    if len(text) <= max_chars:
        chunks.append(text)
        return

    units = [unit.strip() for unit in boundary.split(text) if unit.strip()]
    if len(units) == 1 and boundary is _SENTENCE_BOUNDARY:
        _append_units(chunks, text, max_chars, _SOFT_BOUNDARY)
        return
    if len(units) == 1:
        _append_hard_wrapped(chunks, text, max_chars)
        return

    current = ""
    for unit in units:
        if len(unit) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            _append_units(chunks, unit, max_chars, _SOFT_BOUNDARY)
        elif not current:
            current = unit
        elif len(current) + 1 + len(unit) <= max_chars:
            current = f"{current} {unit}"
        else:
            chunks.append(current)
            current = unit
    if current:
        chunks.append(current)


def _append_hard_wrapped(chunks: list[str], text: str, max_chars: int) -> None:
    remaining = text.strip()
    while len(remaining) > max_chars:
        cut = remaining.rfind(" ", 0, max_chars + 1)
        if cut < max_chars // 2:
            cut = max_chars
        chunks.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        chunks.append(remaining)
