from src.memory.store import MemoryStore


def test_save_and_read_recent_tasks(tmp_path):
    store = MemoryStore(tmp_path)

    cursor = store.save_task({"run_id": "r1", "mode": "quick_chart", "query": "画销售额", "success": True})

    assert cursor == 1
    recent = store.get_recent_tasks(limit=1)
    assert recent[0]["run_id"] == "r1"
    assert recent[0]["cursor"] == 1


def test_skips_corrupt_json_lines(tmp_path):
    history = tmp_path / "task_history.jsonl"
    history.write_text('{"cursor": 1, "mode": "full_report"}\nnot-json\n', encoding="utf-8")

    store = MemoryStore(tmp_path)

    assert len(store.get_recent_tasks(10)) == 1


def test_filters_by_mode_and_chart_type(tmp_path):
    store = MemoryStore(tmp_path)
    store.save_task({"run_id": "r1", "mode": "quick_chart", "chart_types": ["line"], "success": True})
    store.save_task({"run_id": "r2", "mode": "full_report", "chart_types": ["bar"], "success": True})

    assert store.get_tasks_by_mode("full_report")[0]["run_id"] == "r2"
    assert store.get_tasks_by_chart_type("line")[0]["run_id"] == "r1"


def test_build_memory_context_mentions_recent_preferences(tmp_path):
    store = MemoryStore(tmp_path)
    store.save_task({
        "run_id": "r1",
        "mode": "full_report",
        "csv_name": "sales.csv",
        "query": "分析销售",
        "chart_types": ["line"],
        "success": True,
    })

    context = store.build_memory_context("继续分析销售")

    assert "最近的数据分析任务" in context
    assert "full_report" in context
