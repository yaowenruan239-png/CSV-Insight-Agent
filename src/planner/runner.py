from __future__ import annotations

import json
from typing import Any

from src.llm.client import LLMClient
from src.llm.prompts import PLANNER_LOOP_PROMPT
from src.llm.schemas import PlannerAction
from src.planner.models import PlannerStepTrace
from src.skills.registry import SkillRegistry

FINAL_TOOL = "final_answer"


class PlannerLoopRunner:
    def __init__(self, llm: Any | None = None, registry: SkillRegistry | None = None, max_steps: int = 5):
        self.llm = llm or LLMClient()
        self.registry = registry or SkillRegistry()
        self.max_steps = max_steps

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        messages = self._build_messages(state)
        steps: list[dict[str, Any]] = []
        consecutive_failures = 0
        for index in range(1, self.max_steps + 1):
            parsed = self.llm.chat_json_with_trace(messages, schema=PlannerAction)
            if not parsed.get("success"):
                trace = PlannerStepTrace(
                    step_index=index,
                    thought="LLM JSON 解析失败",
                    tool_name="",
                    success=False,
                    error=parsed.get("error"),
                    raw_model_output=parsed.get("raw_text", ""),
                    phase=parsed.get("phase", "llm_parse"),
                )
                steps.append(trace.to_dict())
                consecutive_failures += 1
                if consecutive_failures >= 2:
                    break
                continue

            action = parsed["data"]
            tool_name = action.get("tool_name", "")
            tool_args = action.get("tool_args", {}) or {}
            if tool_name == FINAL_TOOL:
                trace = PlannerStepTrace(
                    step_index=index,
                    thought=action.get("thought", ""),
                    tool_name=tool_name,
                    tool_args=tool_args,
                    normalized_args=tool_args,
                    result_summary=tool_args.get("answer", ""),
                    success=True,
                    raw_model_output=parsed.get("raw_text", ""),
                    phase="final_answer",
                )
                steps.append(trace.to_dict())
                state["final_answer"] = tool_args.get("answer", action.get("thought", ""))
                consecutive_failures = 0
                break

            if not self.registry.get(tool_name):
                trace = PlannerStepTrace(
                    step_index=index,
                    thought=action.get("thought", ""),
                    tool_name=tool_name,
                    tool_args=tool_args,
                    normalized_args=tool_args,
                    success=False,
                    error=f"Unknown planner tool: {tool_name}",
                    raw_model_output=parsed.get("raw_text", ""),
                    phase="validation",
                )
                steps.append(trace.to_dict())
                consecutive_failures += 1
                if consecutive_failures >= 2:
                    break
                continue

            normalized_args = self._normalize_args(tool_name, tool_args, state)
            result = self.registry.call(tool_name, **normalized_args)
            self._merge_result(tool_name, result, state)
            trace = PlannerStepTrace(
                step_index=index,
                thought=action.get("thought", ""),
                tool_name=tool_name,
                tool_args=tool_args,
                normalized_args=normalized_args,
                result_summary=self._summarize_result(result),
                success=bool(result.get("success")),
                error=result.get("error"),
                raw_model_output=parsed.get("raw_text", ""),
                phase="tool_call",
            )
            steps.append(trace.to_dict())
            consecutive_failures = 0 if result.get("success") else consecutive_failures + 1
            messages.append({"role": "assistant", "content": json.dumps(action, ensure_ascii=False)})
            messages.append({"role": "user", "content": f"工具返回：{json.dumps(result, ensure_ascii=False)[:1500]}"})
            if consecutive_failures >= 2:
                break

        state["planner_steps"] = steps
        if not state.get("final_answer"):
            state["final_answer"] = self._interrupted_answer(steps, state)
        return state

    def _build_messages(self, state: dict[str, Any]) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": PLANNER_LOOP_PROMPT + "\n\n可用 Skill:\n" + self.registry.describe_skills()},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "query": state.get("user_query"),
                        "csv_path": state.get("csv_path"),
                        "profile": state.get("dataframe_profile"),
                        "memory": state.get("memory_context"),
                    },
                    ensure_ascii=False,
                ),
            },
        ]

    def _normalize_args(self, tool_name: str, args: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(args)
        if tool_name in {"profile_csv", "plot_chart", "plot_chart_batch"}:
            normalized.setdefault("csv_path", state.get("csv_path"))
        if tool_name in {"plot_chart", "plot_chart_batch", "export_pdf"}:
            normalized.setdefault("run_id", state.get("run_id"))
        if tool_name in {"suggest_chart", "generate_insight", "draft_markdown_report", "export_pdf"}:
            normalized.setdefault("profile", state.get("dataframe_profile", {}))
            normalized.setdefault("query", state.get("user_query", ""))
        if tool_name in {"generate_insight", "draft_markdown_report", "export_pdf"}:
            normalized.setdefault("charts", state.get("generated_charts", []))
        if tool_name in {"draft_markdown_report", "export_pdf"}:
            normalized.setdefault("insights", state.get("analysis_insights", []))
        if tool_name == "plot_chart_batch":
            normalized.setdefault("plans", state.get("chart_plan", []))
        if tool_name == "export_pdf":
            normalized.setdefault("markdown", state.get("report_markdown", ""))
        return {key: value for key, value in normalized.items() if value is not None}

    def _merge_result(self, tool_name: str, result: dict[str, Any], state: dict[str, Any]) -> None:
        if tool_name == "profile_csv" and result.get("success"):
            state["dataframe_profile"] = result
        elif tool_name == "suggest_chart" and result.get("recommended"):
            state["chart_plan"] = result.get("recommended", [])
        elif tool_name == "plot_chart" and result.get("success"):
            state["generated_charts"] = state.get("generated_charts", []) + [result]
        elif tool_name == "plot_chart_batch" and result.get("charts"):
            state["generated_charts"] = result.get("charts", [])
        elif tool_name == "generate_insight" and result.get("insights"):
            state["analysis_insights"] = result.get("insights", [])
        elif tool_name == "draft_markdown_report" and result.get("markdown"):
            state["report_markdown"] = result.get("markdown", "")
        elif tool_name == "export_pdf":
            state["report_path"] = result.get("report_path", "")
            state["pdf_path"] = result.get("pdf_path")
            state["html_path"] = result.get("html_path")
        if result.get("error"):
            state.setdefault("errors", []).append(result["error"])

    def _summarize_result(self, result: dict[str, Any]) -> str:
        if result.get("path"):
            return f"生成文件：{result['path']}"
        if result.get("charts"):
            return f"生成 {len(result['charts'])} 张图表"
        if result.get("recommended"):
            return f"推荐 {len(result['recommended'])} 个图表方案"
        if result.get("markdown"):
            return "生成 Markdown 报告"
        if result.get("report_path"):
            return f"生成报告：{result['report_path']}"
        return str(result)[:200]

    def _interrupted_answer(self, steps: list[dict[str, Any]], state: dict[str, Any]) -> str:
        completed = sum(1 for step in steps if step.get("success"))
        last_error = next((step.get("error") for step in reversed(steps) if step.get("error")), "未知错误")
        chart_count = len(state.get("generated_charts", []))
        return f"Planner Loop 执行中断，但已完成 {completed} 个步骤。失败原因：{last_error}。已生成图表：{chart_count} 张。建议：请尝试 full_report 模式，或明确指定分析目标。"
