from src.graph.nodes.route_node import route_task


def test_route_task_respects_explicit_quick_mode():
    state = {"mode": "quick_chart", "user_query": "画销售趋势"}

    result = route_task(state)

    assert result["route_decision"]["mode"] == "quick_chart"


def test_route_task_respects_explicit_full_report_mode():
    state = {"mode": "full_report", "user_query": "生成完整报告"}

    result = route_task(state)

    assert result["route_decision"]["mode"] == "full_report"


def test_route_task_respects_explicit_planner_mode():
    state = {"mode": "planner_loop", "user_query": "自动规划"}

    result = route_task(state)

    assert result["route_decision"]["mode"] == "planner_loop"


def test_route_task_rule_fallback_to_full_report():
    state = {"mode": "unknown", "user_query": "请生成完整报告"}

    result = route_task(state)

    assert result["route_decision"]["mode"] == "full_report"


def test_route_task_rule_fallback_to_quick_chart():
    state = {"user_query": "画销售趋势"}

    result = route_task(state)

    assert result["route_decision"]["mode"] == "quick_chart"
