from __future__ import annotations

import re
from uuid import UUID

from pydantic import BaseModel

_MARKER_PATTERN = re.compile(r"\[(\d+)\]")


class Citation(BaseModel):
    marker: int
    chunk_id: UUID


class GroundedAnswer(BaseModel):
    answer: str
    citations: list[Citation]
    has_sufficient_evidence: bool


class CitationValidationError(ValueError):
    """Raised when a `GroundedAnswer` fails grounding validation."""


def validate_citations(answer: GroundedAnswer, retrieved_chunk_ids: set[UUID]) -> None:
    """Raise `CitationValidationError` unless `answer` is fully grounded.

    Checks that every `[N]` marker in `answer.answer` has exactly one
    matching `Citation` and vice versa, that every cited `chunk_id` was
    actually retrieved this run, and that `has_sufficient_evidence` is
    consistent with the citation list.
    """
    markers_in_text = {int(marker) for marker in _MARKER_PATTERN.findall(answer.answer)}
    citation_markers = {citation.marker for citation in answer.citations}

    orphaned_markers = markers_in_text - citation_markers
    if orphaned_markers:
        raise CitationValidationError(
            f"Markers {sorted(orphaned_markers)} appear in the answer text but have no matching citation."
        )

    unused_citations = citation_markers - markers_in_text
    if unused_citations:
        raise CitationValidationError(
            f"Citations {sorted(unused_citations)} are not referenced by any marker in the answer text."
        )

    invalid_chunk_ids = {
        citation.chunk_id for citation in answer.citations if citation.chunk_id not in retrieved_chunk_ids
    }
    if invalid_chunk_ids:
        raise CitationValidationError(
            f"Citations reference chunk IDs that were not retrieved this run: {sorted(invalid_chunk_ids, key=str)}. "
            f"Valid chunk IDs are: {sorted(retrieved_chunk_ids, key=str)}."
        )

    if answer.has_sufficient_evidence and not answer.citations:
        raise CitationValidationError("has_sufficient_evidence=True requires at least one citation.")

    if not answer.has_sufficient_evidence and answer.citations:
        raise CitationValidationError("has_sufficient_evidence=False requires an empty citation list.")
