from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import streamlit as st

from src.config import UPLOAD_DIR, ensure_runtime_dirs
from src.graph.builder import create_graph_workflow
from src.llm.client import LLMClient
from src.memory.store import MemoryStore

ensure_runtime_dirs()

st.set_page_config(page_title="CSV-Insight-Agent", layout="wide")
st.title("CSV-Insight-Agent：基于 LangGraph + Skill Registry + Memory 的 CSV 数据分析智能体")
st.caption("上传 CSV，用自然语言生成图表、中文洞察、Markdown/PDF 报告，或运行 JSON Planner Loop。")

store = MemoryStore()
with st.sidebar:
    st.subheader("LLM 后端")
    llm = LLMClient()
    st.write(llm.available_backends() or ["rules fallback"])
    st.subheader("最近任务")
    recent_tasks = store.get_recent_tasks(5)
    if recent_tasks:
        for task in recent_tasks:
            st.caption(f"{task.get('mode')} · {task.get('csv_name')} · {task.get('query')}")
    else:
        st.caption("暂无历史任务")

uploaded = st.file_uploader("上传 CSV", type=["csv"])
mode = st.selectbox(
    "执行模式",
    ["quick_chart", "full_report", "planner_loop"],
    format_func={
        "quick_chart": "Quick Chart Mode：单图 + 中文解释",
        "full_report": "Full Report Mode：多图 + 报告 + PDF/HTML",
        "planner_loop": "Planner Loop Mode：JSON 工具规划",
    }.get,
)
query = st.text_area("分析需求", value="分析这个 CSV 数据并生成有价值的中文洞察。")

if st.button("开始分析", type="primary"):
    if not uploaded:
        st.error("请先上传 CSV 文件。")
        st.stop()

    run_id = uuid4().hex[:12]
    csv_path = UPLOAD_DIR / f"{run_id}_{uploaded.name}"
    csv_path.write_bytes(uploaded.getbuffer())
    state = {
        "run_id": run_id,
        "mode": mode,
        "csv_path": str(csv_path),
        "csv_name": uploaded.name,
        "user_query": query,
        "errors": [],
        "retry_count": 0,
        "status": "running",
    }
    with st.spinner("正在运行 Agent 工作流..."):
        result = create_graph_workflow().invoke(state)

    st.success(f"状态：{result.get('status')}")
    if result.get("errors"):
        st.warning("; ".join(result["errors"]))

    charts = result.get("generated_charts", [])
    if charts:
        st.markdown("### 图表结果")
        for chart in charts:
            path = chart.get("path")
            if path and Path(path).exists():
                st.image(path, caption=chart.get("title"))
                st.download_button("下载图表", Path(path).read_bytes(), file_name=Path(path).name)

    if result.get("final_answer"):
        st.markdown("### 分析结果")
        st.markdown(result["final_answer"])

    if result.get("report_markdown"):
        st.markdown("### 报告预览")
        st.markdown(result["report_markdown"])

    for key, label in [("report_path", "下载 Markdown"), ("pdf_path", "下载 PDF"), ("html_path", "下载 HTML")]:
        path = result.get(key)
        if path and Path(path).exists():
            st.download_button(label, Path(path).read_bytes(), file_name=Path(path).name)

    if result.get("planner_steps"):
        st.markdown("### Planner Loop 步骤")
        st.json(result["planner_steps"])
