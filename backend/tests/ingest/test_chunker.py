import tiktoken
import pytest

from ingest.chunker import ChunkRecord, chunk_markdown


@pytest.fixture(scope="module")
def enc() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")


def para_of(n_tokens: int, enc: tiktoken.Encoding) -> str:
    """Return a string of exactly n_tokens tokens."""
    base = "example word here and there plus more text to fill space. "
    ids = enc.encode(base * 20)[:n_tokens]
    return enc.decode(ids)


# --- basic correctness ---


def test_empty_input_returns_no_chunks() -> None:
    assert chunk_markdown("") == []


def test_whitespace_only_returns_no_chunks() -> None:
    assert chunk_markdown("   \n\n   ") == []


def test_short_doc_is_single_chunk(enc: tiktoken.Encoding) -> None:
    doc = "This is a very short document."
    chunks = chunk_markdown(doc)
    assert len(chunks) == 1
    assert chunks[0].content == doc
    assert chunks[0].chunk_index == 0


def test_chunk_index_contiguous_from_zero(enc: tiktoken.Encoding) -> None:
    para = para_of(60, enc)
    doc = "\n\n".join([para] * 20)
    chunks = chunk_markdown(doc, chunk_size=100, overlap=10)

    assert len(chunks) > 1
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


# --- size constraint ---


def test_no_chunk_exceeds_chunk_size(enc: tiktoken.Encoding) -> None:
    para = para_of(60, enc)
    doc = "\n\n".join([para] * 20)
    chunk_size = 100
    overlap = 10

    chunks = chunk_markdown(doc, chunk_size=chunk_size, overlap=overlap)

    assert len(chunks) > 1
    for chunk in chunks:
        # A chunk may slightly exceed chunk_size by up to the overlap amount
        # when the overlap prefix is prepended to the first paragraph.
        assert chunk.token_count <= chunk_size + overlap


# --- overlap ---


def test_overlap_prefix_appears_at_start_of_next_chunk(enc: tiktoken.Encoding) -> None:
    para = para_of(60, enc)
    doc = "\n\n".join([para] * 10)
    overlap = 10

    chunks = chunk_markdown(doc, chunk_size=100, overlap=overlap)
    assert len(chunks) >= 2

    # The overlap text decoded from the last `overlap` tokens of chunk 0
    # is the same string prepended to chunk 1 by the implementation.
    c0_ids = enc.encode(chunks[0].content)
    expected_prefix = enc.decode(c0_ids[-overlap:]).strip()

    assert chunks[1].content.startswith(expected_prefix)


def test_overlap_carries_forward_across_all_boundaries(enc: tiktoken.Encoding) -> None:
    para = para_of(60, enc)
    doc = "\n\n".join([para] * 15)
    overlap = 10

    chunks = chunk_markdown(doc, chunk_size=100, overlap=overlap)
    assert len(chunks) >= 3

    for i in range(len(chunks) - 1):
        ids = enc.encode(chunks[i].content)
        expected_prefix = enc.decode(ids[-overlap:]).strip()
        assert chunks[i + 1].content.startswith(expected_prefix)


# --- section metadata ---


def test_section_set_from_item_header() -> None:
    doc = "Item 1. Business\n\nThis is the business section content."
    chunks = chunk_markdown(doc)

    for chunk in chunks:
        assert chunk.metadata["section"] == "Item 1. Business"


def test_section_uppercase_item_header() -> None:
    doc = "ITEM 7. MANAGEMENT'S DISCUSSION\n\nContent here."
    chunks = chunk_markdown(doc)

    assert chunks[0].metadata["section"] == "ITEM 7. MANAGEMENT'S DISCUSSION"


def test_section_transitions_at_item_boundary(enc: tiktoken.Encoding) -> None:
    para = para_of(60, enc)
    doc = (
        "Item 7. MD&A\n\n"
        + para + "\n\n"
        + "Item 8. Financial Statements\n\n"
        + para
    )
    chunks = chunk_markdown(doc, chunk_size=100, overlap=10)

    sections = [c.metadata["section"] for c in chunks]
    assert "Item 7. MD&A" in sections
    assert "Item 8. Financial Statements" in sections

    item7_last = max(i for i, c in enumerate(chunks) if c.metadata["section"] == "Item 7. MD&A")
    item8_first = min(i for i, c in enumerate(chunks) if c.metadata["section"] == "Item 8. Financial Statements")
    assert item7_last < item8_first


def test_section_alphanumeric_item_number() -> None:
    doc = "Item 1A. Risk Factors\n\nSome risk factor content."
    chunks = chunk_markdown(doc)

    assert chunks[0].metadata["section"] == "Item 1A. Risk Factors"


# --- metadata keys ---


def test_metadata_has_required_keys() -> None:
    doc = "Item 1. Business\n\nSome content here."
    chunks = chunk_markdown(doc)

    for chunk in chunks:
        assert "section" in chunk.metadata
        assert "char_start" in chunk.metadata
        assert "char_end" in chunk.metadata
        assert isinstance(chunk.metadata["char_start"], int)
        assert isinstance(chunk.metadata["char_end"], int)


def test_char_end_greater_than_char_start() -> None:
    doc = "Item 7. Results\n\nOperating income increased year over year."
    chunks = chunk_markdown(doc)

    for chunk in chunks:
        assert chunk.metadata["char_end"] >= chunk.metadata["char_start"]
