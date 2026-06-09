from __future__ import annotations

import re

import markdownify
from bs4 import BeautifulSoup

# XBRL metadata containers hold schema/context data only — no readable content.
_XBRL_METADATA_TAGS = {"ix:header", "xbrli:xbrl", "xbrl"}

# Matches any namespaced tag (ix:*, xbrli:*, dei:*, us-gaap:*, etc.)
_NS_TAG_RE = re.compile(r"^[a-z][\w-]*:")


def _clean_table(table) -> None:
    """Strip empty spacer rows and columns from an EDGAR HTML table in-place.

    EDGAR financial statements use empty <td> cells as visual spacers between
    data columns and empty <tr> rows as vertical spacers. These produce
    enormous pipe-table rows full of empty cells in the Markdown output.
    """
    rows = table.find_all("tr")
    if not rows:
        return

    # Pass 1: remove rows where every cell has no text content.
    for row in list(rows):
        cells = row.find_all(["td", "th"])
        if cells and all(not c.get_text(strip=True) for c in cells):
            row.decompose()

    # Pass 2: remove columns where every cell across all remaining rows is empty.
    rows = table.find_all("tr")
    if not rows:
        return

    col_cells: dict[int, list] = {}
    for row in rows:
        for i, cell in enumerate(row.find_all(["td", "th"])):
            col_cells.setdefault(i, []).append(cell)

    empty_cols = {
        i for i, cells in col_cells.items()
        if all(not c.get_text(strip=True) for c in cells)
    }
    if not empty_cols:
        return

    for row in rows:
        for i, cell in enumerate(row.find_all(["td", "th"])):
            if i in empty_cols:
                cell.decompose()


def html_to_markdown(html: bytes) -> str:
    """Convert raw SEC EDGAR HTML bytes to normalized Markdown, full fidelity."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(_XBRL_METADATA_TAGS):
        tag.decompose()

    # Unwrap inline XBRL annotations — text content is the financial data we want.
    for tag in soup.find_all(_NS_TAG_RE):
        tag.unwrap()

    for table in soup.find_all("table"):
        _clean_table(table)

    md = markdownify.markdownify(str(soup), heading_style="ATX")
    # Collapse runs of blank lines left by removed blocks.
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()
