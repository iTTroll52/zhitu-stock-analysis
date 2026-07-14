#!/usr/bin/env python3

from __future__ import annotations

import unittest

from short_term_signals import analyze_candidate


def bars_from_closes(closes: list[float]) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for index, close in enumerate(closes, start=1):
        rows.append({
            "t": f"2026-06-{index:02d}",
            "o": close - 0.03,
            "h": close + 0.10,
            "l": close - 0.10,
            "c": close,
            "v": 180 if index == len(closes) else 100,
        })
    return rows


def base_candidate(closes: list[float]) -> dict[str, object]:
    return {
        "code": "600000",
        "name": "测试股份",
        "sector": "测试行业",
        "sector_stage": "strengthening",
        "market_regime": "repairing",
        "quality_score": 95,
        "evidence_score": 65,
        "business_support": "confirmed",
        "bars": bars_from_closes(closes),
    }


class ShortTermSignalTests(unittest.TestCase):
    def test_bottom_start_signal(self) -> None:
        candidate = base_candidate([
            12, 11.5, 11, 10.5, 10, 9.6, 9.3, 9.1, 9.0, 9.05,
            9.1, 9.15, 9.2, 9.25, 9.3, 9.35, 9.4, 9.5, 9.6, 9.7,
        ])
        candidate["sector_stage"] = "starting"
        candidate["quote"] = {"p": 9.9, "yc": 9.7, "o": 9.65, "h": 9.95, "l": 9.6, "pc": 2.06, "hs": 3, "lb": 1.8, "cje": 200_000_000}
        result = analyze_candidate(candidate)
        self.assertIn("bottom_start", result["matched_signals"])
        self.assertEqual(result["primary_signal"], "bottom_start")
        self.assertEqual(result["research_tier"], "priority")

    def test_accelerating_signal(self) -> None:
        closes = [9 + index * 0.15 for index in range(20)]
        candidate = base_candidate(closes)
        candidate["quote"] = {"p": 12.2, "yc": closes[-1], "o": 11.9, "h": 12.3, "l": 11.85, "pc": 2.95, "hs": 6, "lb": 1.8, "cje": 600_000_000}
        result = analyze_candidate(candidate)
        self.assertIn("accelerating", result["matched_signals"])
        self.assertEqual(result["primary_signal"], "accelerating")

    def test_first_limit_up_signal(self) -> None:
        candidate = base_candidate([10 + index * 0.02 for index in range(20)])
        candidate["quote"] = {"p": 11, "yc": 10, "o": 10.2, "h": 11, "l": 10.1, "pc": 10, "hs": 8, "cje": 500_000_000}
        candidate["pool"] = {"is_limit_up": True, "limit_up_price": 11, "lbc": 1, "fbt": "09:35:00", "lbt": "09:40:00", "zbc": 1, "zj": 100_000_000}
        result = analyze_candidate(candidate)
        self.assertIn("limit_up", result["matched_signals"])
        self.assertEqual(result["primary_signal"], "limit_up")

    def test_consecutive_limit_has_precedence(self) -> None:
        candidate = base_candidate([10 + index * 0.02 for index in range(20)])
        candidate["quote"] = {"p": 11, "yc": 10, "o": 10.2, "h": 11, "l": 10.1, "pc": 10, "hs": 8, "cje": 500_000_000}
        candidate["pool"] = {"is_limit_up": True, "limit_up_price": 11, "lbc": 3, "fbt": "09:35:00", "lbt": "09:40:00", "zbc": 1, "zj": 100_000_000}
        result = analyze_candidate(candidate)
        self.assertIn("consecutive_limit_up", result["matched_signals"])
        self.assertEqual(result["primary_signal"], "consecutive_limit_up")

    def test_limit_requires_exact_limit_price(self) -> None:
        candidate = base_candidate([10 + index * 0.02 for index in range(20)])
        candidate["quote"] = {"p": 11, "yc": 10, "o": 10.2, "h": 11, "l": 10.1, "pc": 10, "hs": 8, "cje": 500_000_000}
        candidate["pool"] = {"is_limit_up": True, "lbc": 1, "fbt": "09:35:00", "zbc": 0}
        result = analyze_candidate(candidate)
        self.assertNotIn("limit_up", result["matched_signals"])

    def test_one_word_limit_is_watch_only(self) -> None:
        candidate = base_candidate([10 + index * 0.02 for index in range(20)])
        candidate["quote"] = {"p": 11, "yc": 10, "o": 11, "h": 11, "l": 11, "pc": 10, "hs": 0.2, "cje": 10_000_000}
        candidate["pool"] = {"is_limit_up": True, "limit_up_price": 11, "lbc": 2, "fbt": "09:25:00", "zbc": 0, "zj": 50_000_000}
        result = analyze_candidate(candidate)
        self.assertEqual(result["research_tier"], "watch_only")
        self.assertTrue(any("one-word" in flag for flag in result["no_chase_flags"]))

    def test_insufficient_history_is_excluded(self) -> None:
        candidate = base_candidate([10, 10.1, 10.2])
        candidate["quote"] = {"p": 10.3, "yc": 10.2, "pc": 0.98}
        result = analyze_candidate(candidate)
        self.assertFalse(result["eligible_for_signals"])


if __name__ == "__main__":
    unittest.main()
