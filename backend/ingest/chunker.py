from __future__ import annotations

import re
from dataclasses import dataclass

import tiktoken

CHUNK_SIZE = 500
OVERLAP = 50

_SECTION_RE = re.compile(r"^\s*#{0,6}\s*Item\s+\d+[A-Za-z]?", re.IGNORECASE)
_SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass
class ChunkRecord:
    content: str
    token_count: int
    chunk_index: int
    metadata: dict  # keys: section, char_start, char_end


@dataclass
class _Unit:
    text: str
    token_count: int
    char_start: int
    char_end: int
    section: str


def chunk_markdown(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = OVERLAP,
) -> list[ChunkRecord]:
    enc = tiktoken.get_encoding("cl100k_base")
    units = _build_units(text, enc, chunk_size)
    if not units:
        return []
    return _pack_chunks(units, enc, chunk_size, overlap)


def _build_units(text: str, enc: tiktoken.Encoding, chunk_size: int) -> list[_Unit]:
    units: list[_Unit] = []
    section = ""
    pos = 0

    for para in text.split("\n\n"):
        char_start = pos
        char_end = pos + len(para)
        pos = char_end + 2  # +2 for the \n\n separator

        stripped = para.strip()
        if not stripped:
            continue

        if _SECTION_RE.match(stripped):
            section = stripped

        tokens = enc.encode(stripped)
        if len(tokens) <= chunk_size:
            units.append(_Unit(stripped, len(tokens), char_start, char_end, section))
        else:
            units.extend(_split_paragraph(stripped, enc, chunk_size, char_start, section))

    return units


def _split_paragraph(
    para: str,
    enc: tiktoken.Encoding,
    chunk_size: int,
    char_offset: int,
    section: str,
) -> list[_Unit]:
    units: list[_Unit] = []
    sub_pos = char_offset

    for sent in _SENTENCE_END_RE.split(para):
        sent = sent.strip()
        if not sent:
            continue
        char_end = sub_pos + len(sent)
        units.append(_Unit(sent, len(enc.encode(sent)), sub_pos, char_end, section))
        sub_pos = char_end + 1  # +1 approximates the whitespace consumed by the split

    return units


def _pack_chunks(
    units: list[_Unit],
    enc: tiktoken.Encoding,
    chunk_size: int,
    overlap: int,
) -> list[ChunkRecord]:
    chunks: list[ChunkRecord] = []
    overlap_prefix = ""
    overlap_token_count = 0
    buf: list[_Unit] = []
    buf_tokens = 0

    i = 0
    while i < len(units):
        unit = units[i]

        if buf and buf_tokens + unit.token_count > chunk_size:
            chunk = _make_chunk(overlap_prefix, buf, enc, len(chunks))
            chunks.append(chunk)

            ids = enc.encode(chunk.content)
            overlap_ids = ids[-overlap:]
            overlap_prefix = enc.decode(overlap_ids)
            overlap_token_count = len(overlap_ids)

            buf = []
            buf_tokens = overlap_token_count
            continue  # retry this unit in the new chunk

        buf.append(unit)
        buf_tokens += unit.token_count
        i += 1

    if buf:
        chunks.append(_make_chunk(overlap_prefix, buf, enc, len(chunks)))

    return chunks


def _make_chunk(
    overlap_prefix: str,
    units: list[_Unit],
    enc: tiktoken.Encoding,
    index: int,
) -> ChunkRecord:
    body = "\n\n".join(u.text for u in units)
    stripped_prefix = overlap_prefix.strip()
    content = (stripped_prefix + "\n\n" + body) if stripped_prefix else body
    return ChunkRecord(
        content=content,
        token_count=len(enc.encode(content)),
        chunk_index=index,
        metadata={
            "section": units[0].section,
            "char_start": units[0].char_start,
            "char_end": units[-1].char_end,
        },
    )
