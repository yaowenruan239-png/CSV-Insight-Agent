import json

from src.graph.state import GraphState
from src.llm.client import LLMClient
from src.llm.prompts import PLANNER_LOOP_PROMPT
from src.llm.schemas import PlannerAction
from src.skills.chart_plot import PlotChartBatchSkill, PlotChartSkill
from src.skills.chart_suggest import SuggestChartSkill
from src.skills.csv_profile import ProfileCSVSkill
from src.skills.insight_generate import GenerateInsightSkill
from src.skills.registry import SkillRegistry
from src.skills.report_draft import DraftMarkdownReportSkill


def build_default_registry() -> SkillRegistry:
    registry = SkillRegistry()
    for skill in [
        ProfileCSVSkill(),
        SuggestChartSkill(),
        PlotChartSkill(),
        PlotChartBatchSkill(),
        GenerateInsightSkill(),
        DraftMarkdownReportSkill(),
    ]:
        registry.register(skill)
    return registry


def json_planner_loop(state: GraphState) -> GraphState:
    registry = build_default_registry()
    llm = LLMClient()
    messages = [
        {"role": "system", "content": PLANNER_LOOP_PROMPT + "\n\n可用 Skill:\n" + registry.describe_skills()},
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
    steps = []
    for _ in range(4):
        action = llm.chat_json(
            messages,
            schema=PlannerAction,
            fallback={"thought": "fallback", "tool_name": "final_answer", "tool_args": {"answer": "Planner Loop 暂不可用，已使用回退回答。"}},
        )
        steps.append(action)
        if action.get("tool_name") == "final_answer":
            state["final_answer"] = action.get("tool_args", {}).get("answer", action.get("thought", ""))
            break
        result = registry.call(action.get("tool_name", ""), **action.get("tool_args", {}))
        if action.get("tool_name") == "plot_chart" and result.get("success"):
            state["generated_charts"] = state.get("generated_charts", []) + [result]
        messages.append({"role": "assistant", "content": json.dumps(action, ensure_ascii=False)})
        messages.append({"role": "user", "content": f"工具返回：{json.dumps(result, ensure_ascii=False)[:1500]}"})
    state["planner_steps"] = steps
    return state
