import json
import tempfile
import unittest
from pathlib import Path

from generate_html_report import build_html, main, validate_analysis_payload


class HtmlReportTests(unittest.TestCase):
    def test_production_rejects_demo_markers(self):
        with self.assertRaisesRegex(ValueError, "demo/simulated/placeholder"):
            validate_analysis_payload({"analysis_mode": "production", "subtitle": "这是演示数据"})

    def test_demo_requires_explicit_allow_flag(self):
        payload = {"analysis_mode": "demo", "title": "演示"}
        with self.assertRaisesRegex(ValueError, "--allow-demo"):
            validate_analysis_payload(payload)
        self.assertEqual(validate_analysis_payload(payload, allow_demo=True), "demo")

    def test_production_candidates_require_quality_cutoff_real_codes_and_sources(self):
        valid = {
            "analysis_mode": "production",
            "data_cutoff": "2026-07-15 15:00 CST",
            "data_quality": {"score": 90},
            "market_regime": {"decision_allowed": True, "regime": "structural_bull", "posture": "selective_participation"},
            "strategy_validation": {"status": "out_of_sample_validated"},
            "candidates": [{"code": "600000", "name": "候选", "research_tier": "priority"}],
            "sources": [{"url": "https://example.com/source"}],
        }
        self.assertEqual(validate_analysis_payload(valid), "production")
        invalid = dict(valid)
        invalid["candidates"] = [{"code": "60XXXX", "name": "占位"}]
        with self.assertRaises(ValueError):
            validate_analysis_payload(invalid)

    def test_production_candidates_rejected_when_market_is_cash(self):
        payload = {
            "analysis_mode": "production",
            "data_cutoff": "2026-07-15 15:00 CST",
            "data_quality": {"score": 90},
            "market_regime": {"decision_allowed": True, "regime": "broad_bear", "posture": "cash"},
            "strategy_validation": {"status": "out_of_sample_validated"},
            "candidates": [{"code": "600000", "research_tier": "priority"}],
            "sources": [{"url": "https://example.com/source"}],
        }
        with self.assertRaisesRegex(ValueError, "market posture"):
            validate_analysis_payload(payload)

    def test_unvalidated_rules_only_allow_watch_candidates(self):
        payload = {
            "analysis_mode": "production",
            "data_cutoff": "2026-07-15 15:00 CST",
            "data_quality": {"score": 90},
            "market_regime": {"decision_allowed": True, "regime": "range", "posture": "wait_or_selective"},
            "strategy_validation": {"status": "experimental"},
            "candidates": [{"code": "600000", "research_tier": "experimental_watch"}],
            "sources": [{"url": "https://example.com/source"}],
        }
        self.assertEqual(validate_analysis_payload(payload), "production")
        payload["candidates"] = [{"code": "600000", "research_tier": "priority"}]
        with self.assertRaisesRegex(ValueError, "experimental/watch"):
            validate_analysis_payload(payload)

    def test_demo_html_has_visible_warning(self):
        report = build_html({"analysis_mode": "demo", "title": "演示"})
        self.assertIn("演示 / 测试数据 · 非真实行情 · 不得用于交易", report)

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
        self.assertIn("市场状态与参与、等待、空仓", report)
        self.assertIn("事件、注意力与价格背离", report)
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
