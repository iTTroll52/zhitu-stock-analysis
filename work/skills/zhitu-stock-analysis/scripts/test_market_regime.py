#!/usr/bin/env python3

from __future__ import annotations

import unittest

from market_regime import analyze


def base_payload() -> dict:
    return {
        "analysis_mode": "production",
        "cutoff_time": "2026-07-15T14:30:00+08:00",
        "source_time": "2026-07-15T14:29:00+08:00",
        "data_quality": {"score": 92},
        "strategy_validation": {"status": "out_of_sample_validated"},
    }


class MarketRegimeTests(unittest.TestCase):
    def test_broad_bull_participation(self) -> None:
        payload = {
            **base_payload(),
            "indices": [{"change_pct": 1.5}, {"change_pct": 1.2}, {"change_pct": 1.8}],
            "breadth": {"advancers": 3600, "decliners": 1200, "above_ma20_pct": 68},
            "liquidity": {"same_time_amount_ratio": 1.2},
            "limits": {"limit_up": 90, "limit_down": 5, "broken": 10},
            "sectors": {"strengthening": 10, "accelerating": 5, "diverging": 1, "fading": 2},
        }
        result = analyze(payload)
        self.assertEqual(result["regime"], "broad_bull")
        self.assertEqual(result["posture"], "participate")
        self.assertTrue(result["decision_allowed"])

    def test_crisis_returns_cash(self) -> None:
        payload = {
            **base_payload(),
            "indices": [{"change_pct": -3}, {"change_pct": -4}],
            "breadth": {"advancers": 600, "decliners": 4200, "above_ma20_pct": 18},
            "liquidity": {"same_time_amount_ratio": 1.4},
            "limits": {"limit_up": 12, "limit_down": 80, "broken": 20},
            "sectors": {"strengthening": 0, "accelerating": 0, "diverging": 4, "fading": 15},
        }
        result = analyze(payload)
        self.assertEqual(result["regime"], "crisis")
        self.assertEqual(result["posture"], "cash")

    def test_missing_cutoff_blocks_decision(self) -> None:
        payload = {
            **base_payload(),
            "cutoff_time": None,
            "indices": [{"change_pct": 1}],
            "breadth": {"advancers": 3000, "decliners": 1500, "above_ma20_pct": 60},
            "liquidity": {"same_time_amount_ratio": 1.1},
            "limits": {"limit_up": 60, "limit_down": 10, "broken": 10},
            "sectors": {"strengthening": 6, "accelerating": 2, "diverging": 1, "fading": 2},
        }
        result = analyze(payload)
        self.assertFalse(result["decision_allowed"])
        self.assertEqual(result["publication_status"], "blocked")
        self.assertIsNone(result["research_exposure_band"])

    def test_unvalidated_rule_is_explicitly_experimental(self) -> None:
        payload = {
            **base_payload(),
            "strategy_validation": {"status": "unvalidated"},
            "indices": [{"change_pct": 0.5}, {"change_pct": 0.3}],
            "breadth": {"advancers": 2700, "decliners": 1900, "above_ma20_pct": 55},
            "liquidity": {"same_time_amount_ratio": 1.05},
            "limits": {"limit_up": 45, "limit_down": 12, "broken": 15},
            "sectors": {"strengthening": 5, "accelerating": 1, "diverging": 2, "fading": 3},
        }
        result = analyze(payload)
        self.assertEqual(result["publication_status"], "experimental_research_state")


if __name__ == "__main__":
    unittest.main()
