import html2text
import re
from datetime import datetime, timezone

def html_to_markdown(html: str, source_url: str = "", title: str = "") -> str:
    """
    Converts HTML to clean Markdown.
    Uses html2text with specific options.
    """
    h = html2text.HTML2Text()
    h.body_width = 0  # Disable line wrapping
    h.ignore_links = False
    h.ignore_images = False
    h.ignore_emphasis = False
    h.mark_code = True
    h.escape_snob = True
    h.protect_links = True
    
    # Process HTML to Markdown
    md_content = h.handle(html)
    
    # Clean up: remove 3+ consecutive blank lines -> 2 blank lines
    md_content = re.sub(r'\n{4,}', '\n\n\n', md_content)
    md_content = md_content.strip() + '\n'
    
    # Prepend YAML frontmatter if source_url or title provided
    if source_url or title:
        now_iso = datetime.now(timezone.utc).isoformat()
        frontmatter = (
            "---\n"
            f"title: {title}\n"
            f"source: {source_url}\n"
            f"fetched: {now_iso}\n"
            "---\n\n"
        )
        md_content = frontmatter + md_content
        
    return md_content

def article_result_to_markdown(result: dict, source_url: str = "") -> str:
    """
    Takes A-Parser result dict and converts its content to markdown.
    """
    content = ""
    
    # Extract content
    if "data" in result:
        if "results" in result["data"] and len(result["data"]["results"]) > 0:
            if "content" in result["data"]["results"][0]:
                content = result["data"]["results"][0]["content"]
        elif "resultString" in result["data"]:
            content = result["data"]["resultString"]
            
    if not content:
        return ""
        
    # Check if content looks like HTML
    if '<' in content and '>' in content:
        return html_to_markdown(content, source_url=source_url)
    
    # Already plain text
    md_content = content
    
    # Clean up: remove 3+ consecutive blank lines -> 2 blank lines
    md_content = re.sub(r'\n{4,}', '\n\n\n', md_content)
    md_content = md_content.strip() + '\n'
    
    # Wrap in frontmatter
    now_iso = datetime.now(timezone.utc).isoformat()
    frontmatter = (
        "---\n"
        f"title: \n"
        f"source: {source_url}\n"
        f"fetched: {now_iso}\n"
        "---\n\n"
    )
    return frontmatter + md_content
