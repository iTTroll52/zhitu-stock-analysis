import json
import tempfile
import unittest
from pathlib import Path

from generate_html_report import build_html, main


class HtmlReportTests(unittest.TestCase):
    def test_build_html_escapes_untrusted_content(self):
        report = build_html({"title": "<script>alert(1)</script>", "candidates": []})
        self.assertNotIn("<script>alert(1)</script>", report)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", report)
        self.assertIn("打印 / PDF", report)

    def test_report_contains_required_sections(self):
        report = build_html(
            {
                "data_cutoff": "2026-07-15 15:00 CST",
                "data_quality": {"score": 91},
                "rotation": {"stage": "strengthening", "current": "强化"},
                "signals": [{"key": "bottom_start", "count": 2}],
                "candidates": [{"code": "600000", "name": "示例", "primary_signal": "bottom_start"}],
            }
        )
        for heading in ("大盘与海外传导", "板块轮动：现在轮到哪里", "条件式候选与模型仓位", "来源与可追溯性"):
            self.assertIn(heading, report)
        self.assertIn("data-signal=\"bottom_start\"", report)

    def test_cli_writes_utf8_html(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "input.json"
            target = root / "report.html"
            source.write_text(json.dumps({"title": "中文报告"}, ensure_ascii=False), encoding="utf-8")
            import sys
            previous = sys.argv
            try:
                sys.argv = ["generate_html_report.py", str(source), "--output", str(target)]
                self.assertEqual(main(), 0)
            finally:
                sys.argv = previous
            self.assertIn("中文报告", target.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
