from __future__ import annotations

import json
from typing import Any

from src.llm.client import LLMClient
from src.llm.prompts import REPORT_PROMPT
from src.skills.base import BaseSkill


class DraftMarkdownReportSkill(BaseSkill):
    name = "draft_markdown_report"
    description = "生成完整中文 Markdown 数据分析报告。"
    args_schema = {"type": "object", "properties": {"profile": {"type": "object"}, "charts": {"type": "array"}}, "required": ["profile"]}

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def run(self, **kwargs: Any) -> dict[str, Any]:
        try:
            markdown = self.llm.chat([
                {"role": "system", "content": REPORT_PROMPT},
                {"role": "user", "content": json.dumps(kwargs, ensure_ascii=False)[:10000]},
            ])
        except Exception:
            markdown = self._fallback_report(kwargs)
        return {"success": True, "markdown": markdown}

    def _fallback_report(self, data: dict[str, Any]) -> str:
        profile = data.get("profile", {})
        charts = data.get("charts", [])
        chart_lines = "\n".join(f"![{chart.get('title', '图表')}]({chart.get('path')})" for chart in charts)
        insight_lines = "\n".join(f"- {item}" for item in data.get("insights", [])) or "- 当前报告基于数据画像和图表自动生成。"
        return f"""# 数据分析报告

## 1. 数据概况

数据集包含 {profile.get('rows', 0)} 行、{profile.get('columns', 0)} 列。

## 2. 分析目标

{data.get('query', '分析 CSV 数据。')}

## 3. 核心发现

{insight_lines}

## 4. 图表分析

{chart_lines or '未生成图表。'}

## 5. 综合结论

当前报告基于数据画像和图表结果生成。

## 6. 建议

建议结合业务背景进一步验证图表中的异常和趋势。

## 7. 局限性说明

本报告仅基于上传 CSV 的现有字段和记录生成，不代表外部事实。
"""
