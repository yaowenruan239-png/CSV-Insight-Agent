from src.graph.nodes.planner_loop_node import build_default_registry
from src.planner.runner import PlannerLoopRunner


class FakeLLM:
    def __init__(self, results):
        self.results = list(results)

    def chat_json_with_trace(self, messages, schema=None):
        return self.results.pop(0)


def base_state(tmp_path):
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("月份,销售额\n1月,100\n2月,120\n", encoding="utf-8")
    return {
        "run_id": "r1",
        "csv_path": str(csv_path),
        "user_query": "分析销售趋势",
        "dataframe_profile": {"rows": 2, "columns": 2, "column_names": ["月份", "销售额"], "numeric_columns": ["销售额"]},
        "memory_context": "暂无历史记忆。",
        "generated_charts": [],
        "analysis_insights": [],
        "errors": [],
    }


def test_default_planner_registry_matches_prompt_tools():
    registry = build_default_registry()
    names = {skill["name"] for skill in registry.list_skills()}

    assert {"profile_csv", "suggest_chart", "plot_chart", "plot_chart_batch", "generate_insight", "draft_markdown_report", "export_pdf", "read_recent_memory", "save_memory"}.issubset(names)


def test_planner_runner_records_tool_steps(tmp_path):
    llm = FakeLLM([
        {"success": True, "phase": "ok", "error": None, "raw_text": "{}", "data": {"thought": "推荐图表", "tool_name": "suggest_chart", "tool_args": {}}},
        {"success": True, "phase": "ok", "error": None, "raw_text": "{}", "data": {"thought": "结束", "tool_name": "final_answer", "tool_args": {"answer": "完成分析"}}},
    ])
    runner = PlannerLoopRunner(llm=llm, registry=build_default_registry(), max_steps=3)

    result = runner.run(base_state(tmp_path))

    assert result["final_answer"] == "完成分析"
    assert len(result["planner_steps"]) == 2
    assert result["planner_steps"][0]["tool_name"] == "suggest_chart"
    assert result["planner_steps"][0]["success"] is True


def test_planner_runner_autofills_csv_path_and_run_id(tmp_path):
    llm = FakeLLM([
        {"success": True, "phase": "ok", "error": None, "raw_text": "{}", "data": {"thought": "画图", "tool_name": "plot_chart", "tool_args": {"chart_type": "bar", "x_col": "月份", "y_col": "销售额", "title": "销售趋势"}}},
        {"success": True, "phase": "ok", "error": None, "raw_text": "{}", "data": {"thought": "结束", "tool_name": "final_answer", "tool_args": {"answer": "已生成图表"}}},
    ])
    runner = PlannerLoopRunner(llm=llm, registry=build_default_registry(), max_steps=3)

    result = runner.run(base_state(tmp_path))

    args = result["planner_steps"][0]["normalized_args"]
    assert args["csv_path"].endswith("data.csv")
    assert args["run_id"] == "r1"
    assert result["generated_charts"]


def test_planner_runner_records_unknown_tool_error(tmp_path):
    llm = FakeLLM([
        {"success": True, "phase": "ok", "error": None, "raw_text": "{}", "data": {"thought": "调用未知工具", "tool_name": "missing_tool", "tool_args": {}}},
        {"success": True, "phase": "ok", "error": None, "raw_text": "{}", "data": {"thought": "结束", "tool_name": "final_answer", "tool_args": {"answer": "结束"}}},
    ])
    runner = PlannerLoopRunner(llm=llm, registry=build_default_registry(), max_steps=3)

    result = runner.run(base_state(tmp_path))

    assert result["planner_steps"][0]["success"] is False
    assert result["planner_steps"][0]["phase"] == "validation"
    assert "Unknown planner tool" in result["planner_steps"][0]["error"]


def test_planner_runner_returns_final_answer_without_silent_fallback(tmp_path):
    llm = FakeLLM([
        {"success": False, "phase": "llm_parse", "error": "No JSON object found", "raw_text": "bad", "data": None},
        {"success": False, "phase": "llm_parse", "error": "No JSON object found", "raw_text": "bad", "data": None},
    ])
    runner = PlannerLoopRunner(llm=llm, registry=build_default_registry(), max_steps=3)

    result = runner.run(base_state(tmp_path))

    assert "Planner Loop 执行中断" in result["final_answer"]
    assert len(result["planner_steps"]) == 2
    assert result["planner_steps"][0]["error"] == "No JSON object found"
