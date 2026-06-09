from ingest.parser import html_to_markdown


def test_heading_converted_to_atx() -> None:
    md = html_to_markdown(b"<h1>Annual Report</h1>")
    assert "# Annual Report" in md


def test_subheadings_use_atx_style() -> None:
    md = html_to_markdown(b"<h2>Item 7</h2><h3>Revenue</h3>")
    assert "## Item 7" in md
    assert "### Revenue" in md


def test_table_converted_to_pipe_table() -> None:
    html = b"""
    <table>
      <tr><th>Year</th><th>Revenue</th></tr>
      <tr><td>2023</td><td>$33.7B</td></tr>
    </table>"""
    md = html_to_markdown(html)
    assert "|" in md
    assert "Year" in md
    assert "Revenue" in md
    assert "2023" in md
    assert "$33.7B" in md


def test_unordered_list_converted() -> None:
    html = b"<ul><li>Risk one</li><li>Risk two</li></ul>"
    md = html_to_markdown(html)
    assert "Risk one" in md
    assert "Risk two" in md


def test_nested_list_converted() -> None:
    html = b"""
    <ul>
      <li>Risk factor one
        <ul><li>Sub-risk A</li></ul>
      </li>
    </ul>"""
    md = html_to_markdown(html)
    assert "Risk factor one" in md
    assert "Sub-risk A" in md


def test_xbrl_inline_tag_text_preserved() -> None:
    html = b'<p>Revenue was <ix:nonfraction contextRef="c1" decimals="-6">33723</ix:nonfraction> million.</p>'
    md = html_to_markdown(html)
    assert "33723" in md
    assert "ix:nonfraction" not in md
    assert "contextRef" not in md
    assert "decimals" not in md


def test_xbrl_nonnumeric_tag_text_preserved() -> None:
    html = b'<p><ix:nonnumeric contextRef="c1" name="dei:EntityName">Netflix, Inc.</ix:nonnumeric></p>'
    md = html_to_markdown(html)
    assert "Netflix, Inc." in md
    assert "ix:nonnumeric" not in md


def test_xbrl_header_block_removed() -> None:
    html = b"""<html><body>
    <ix:header><ix:references/><ix:resources/></ix:header>
    <p>Actual content here.</p>
    </body></html>"""
    md = html_to_markdown(html)
    assert "Actual content here." in md
    assert "ix:header" not in md
    assert "ix:references" not in md


def test_returns_stripped_string() -> None:
    md = html_to_markdown(b"<p>Hello</p>")
    assert md == md.strip()


def test_no_excessive_blank_lines() -> None:
    html = b"<p>First</p>\n\n\n\n\n<p>Second</p>"
    md = html_to_markdown(html)
    assert "\n\n\n" not in md


def test_empty_table_rows_removed() -> None:
    # EDGAR uses <tr><td></td><td></td></tr> as vertical spacers.
    html = b"""
    <table>
      <tr><td></td><td></td></tr>
      <tr><th>Year</th><th>Revenue</th></tr>
      <tr><td></td><td></td></tr>
      <tr><td>2023</td><td>$33.7B</td></tr>
    </table>"""
    md = html_to_markdown(html)
    # Data must be present.
    assert "Year" in md
    assert "2023" in md
    # An all-empty table row renders as |  |  | — this should be absent.
    rows = [line for line in md.splitlines() if line.strip().startswith("|")]
    for row in rows:
        cells = [c.strip() for c in row.strip("|").split("|")]
        assert any(c for c in cells), f"all-empty row should have been removed: {row!r}"


def test_empty_table_columns_removed() -> None:
    # EDGAR uses empty <td> cells as horizontal spacers between data columns.
    html = b"""
    <table>
      <tr><th>Year</th><td></td><th>Revenue</th></tr>
      <tr><td>2023</td><td></td><td>$33.7B</td></tr>
    </table>"""
    md = html_to_markdown(html)
    assert "Year" in md
    assert "Revenue" in md
    assert "2023" in md
    assert "$33.7B" in md
    # The empty spacer column should not produce a run of consecutive empty cells.
    for row in md.splitlines():
        if "|" not in row:
            continue
        assert "||" not in row.replace(" ", ""), (
            f"consecutive empty cells indicate spacer column was not removed: {row!r}"
        )
