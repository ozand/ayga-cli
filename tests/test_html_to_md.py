import pytest
import re
from ayga_cli.utils.html_to_md import html_to_markdown, article_result_to_markdown

def test_html_to_markdown_basic():
    html = "<h1>Title</h1><p>Body</p>"
    md = html_to_markdown(html)
    assert "# Title" in md
    assert "Body" in md

def test_html_to_markdown_with_frontmatter():
    html = "<p>Content</p>"
    md = html_to_markdown(html, source_url="https://example.com")
    assert md.startswith("---")
    assert "source: https://example.com" in md
    assert "fetched:" in md
    assert "Content" in md

def test_article_result_to_markdown():
    result = {
        "data": {
            "resultString": "<h2>Test</h2><p>Article</p>"
        }
    }
    md = article_result_to_markdown(result, source_url="https://test.com")
    assert md.startswith("---")
    assert "## Test" in md
    assert "Article" in md

def test_cleanup_blank_lines():
    html = "<h1>Title</h1><br><br><br><br><br><p>Body</p>"
    md = html_to_markdown(html)
    
    # Should have at most 2 consecutive blank lines
    # which means at most 3 consecutive newline characters
    matches = re.findall(r'\n{4,}', md)
    assert len(matches) == 0
