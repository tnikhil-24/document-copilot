from __future__ import annotations

from uuid import uuid4

import pytest

from app.grounding.validator import (
    Citation,
    CitationValidationError,
    GroundedAnswer,
    validate_citations,
)


class TestValidateCitations:
    def test_valid_grounded_answer_passes(self) -> None:
        chunk_id = uuid4()
        answer = GroundedAnswer(
            answer="Content costs rose 15% in 2023 [1].",
            citations=[Citation(marker=1, chunk_id=chunk_id)],
            has_sufficient_evidence=True,
        )

        validate_citations(answer, {chunk_id})

    def test_valid_refusal_passes(self) -> None:
        answer = GroundedAnswer(
            answer="The corpus does not contain enough information to answer this question.",
            citations=[],
            has_sufficient_evidence=False,
        )

        validate_citations(answer, {uuid4()})

    def test_marker_with_no_matching_citation_raises(self) -> None:
        chunk_id = uuid4()
        answer = GroundedAnswer(
            answer="Content costs rose [1] and revenue grew [2].",
            citations=[Citation(marker=1, chunk_id=chunk_id)],
            has_sufficient_evidence=True,
        )

        with pytest.raises(CitationValidationError):
            validate_citations(answer, {chunk_id})

    def test_citation_with_no_matching_marker_raises(self) -> None:
        chunk_id = uuid4()
        answer = GroundedAnswer(
            answer="Content costs rose [1].",
            citations=[
                Citation(marker=1, chunk_id=chunk_id),
                Citation(marker=2, chunk_id=uuid4()),
            ],
            has_sufficient_evidence=True,
        )

        with pytest.raises(CitationValidationError):
            validate_citations(answer, {chunk_id})

    def test_citation_referencing_unretrieved_chunk_id_raises(self) -> None:
        retrieved_chunk_id = uuid4()
        unretrieved_chunk_id = uuid4()
        answer = GroundedAnswer(
            answer="Content costs rose [1].",
            citations=[Citation(marker=1, chunk_id=unretrieved_chunk_id)],
            has_sufficient_evidence=True,
        )

        with pytest.raises(CitationValidationError):
            validate_citations(answer, {retrieved_chunk_id})

    def test_sufficient_evidence_true_with_empty_citations_raises(self) -> None:
        answer = GroundedAnswer(
            answer="Content costs rose significantly.",
            citations=[],
            has_sufficient_evidence=True,
        )

        with pytest.raises(CitationValidationError):
            validate_citations(answer, set())

    def test_sufficient_evidence_false_with_citations_raises(self) -> None:
        chunk_id = uuid4()
        answer = GroundedAnswer(
            answer="Content costs rose [1].",
            citations=[Citation(marker=1, chunk_id=chunk_id)],
            has_sufficient_evidence=False,
        )

        with pytest.raises(CitationValidationError):
            validate_citations(answer, {chunk_id})
