from __future__ import annotations

from html import escape
from pathlib import Path

import markdown as markdown_lib


def markdown_to_html(markdown_text: str, title: str = "CSV Insight Report") -> str:
    body = markdown_lib.markdown(markdown_text, extensions=["tables", "fenced_code"])
    return f"""<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>{escape(title)}</title>
<style>body{{font-family:Arial,'Microsoft YaHei',sans-serif;max-width:960px;margin:32px auto;line-height:1.7}} img{{max-width:100%}}</style></head>
<body>{body}</body></html>"""


def write_text(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return str(path)
