from src.graph.state import GraphState
from src.skills.chart_plot import PlotChartBatchSkill, PlotChartSkill


def execute_chart(state: GraphState) -> GraphState:
    result = PlotChartSkill().run(csv_path=state["csv_path"], run_id=state["run_id"], **state.get("chart_plan", {}))
    state["generated_charts"] = [result] if result.get("success") else []
    if not result.get("success"):
        state.setdefault("errors", []).append(result.get("error", "chart failed"))
    return state


def execute_chart_batch(state: GraphState) -> GraphState:
    result = PlotChartBatchSkill().run(csv_path=state["csv_path"], run_id=state["run_id"], plans=state.get("chart_plan", []))
    state["generated_charts"] = result.get("charts", [])
    if result.get("errors"):
        state.setdefault("errors", []).extend(str(error) for error in result["errors"])
    return state
