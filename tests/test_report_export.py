from pathlib import Path

from src.skills.export_pdf import ExportPDFSkill


def test_export_markdown_creates_report_and_export_file(tmp_path):
    skill = ExportPDFSkill(report_dir=tmp_path / "reports", html_dir=tmp_path / "html")

    result = skill.run(run_id="r1", markdown="# 测试报告\n\n内容")

    assert result["success"] is True
    assert Path(result["report_path"]).exists()
    assert result["pdf_path"] or result["html_path"]
    if result["pdf_path"]:
        assert Path(result["pdf_path"]).exists()
    if result["html_path"]:
        assert Path(result["html_path"]).exists()
