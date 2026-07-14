#!/usr/bin/env python3

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from data_quality import validate_bars, validate_limit_pool
from evidence_gate import evaluate as evaluate_evidence
from research_tracker import connect, evaluate, record_signals, record_snapshots, report
from screen_main_board import eligibility, run_screen, score_market_record
from sector_rotation import analyze, classify
from zhitu_client import CacheStore, ZhituClient


class EligibilityTests(unittest.TestCase):
    def test_main_board_allowed(self) -> None:
        self.assertEqual(eligibility("600000", "浦发银行", set()), (True, "eligible"))

    def test_st_and_non_main_board_excluded(self) -> None:
        self.assertFalse(eligibility("000001", "ST测试", set())[0])
        self.assertFalse(eligibility("300001", "测试", set())[0])
        self.assertFalse(eligibility("688001", "测试", set())[0])


class ScoringTests(unittest.TestCase):
    def test_score_is_deterministic_and_bounded(self) -> None:
        row = {"cje": 900_000_000, "pc": 6.5, "hs": 5, "p": 11, "o": 10.5, "yc": 10, "zf": 5, "pe": 25}
        first = score_market_record(row)
        second = score_market_record(row)
        self.assertEqual(first, second)
        self.assertGreaterEqual(first["pre_screen_score"], 0)
        self.assertLessEqual(first["pre_screen_score"], 100)
        self.assertIn("pending", first["label"])

    def test_full_market_screen_uses_one_market_snapshot(self) -> None:
        class Result:
            def __init__(self, payload: object, endpoint: str) -> None:
                self.payload = payload
                self.endpoint = endpoint

            def lineage(self) -> dict[str, str]:
                return {"endpoint": self.endpoint}

        class Client:
            def __init__(self) -> None:
                self.calls: list[str] = []

            def get(self, endpoint: str, **_: object) -> Result:
                self.calls.append(endpoint)
                if endpoint == "stock_list":
                    return Result([{"dm": "600000", "mc": "测试银行", "jys": "sh"}], endpoint)
                if endpoint == "st_list":
                    return Result([], endpoint)
                if endpoint == "all_market":
                    return Result([{
                        "dm": "600000", "p": 10.1, "yc": 10, "o": 10, "h": 10.2, "l": 9.9,
                        "pc": 1, "zf": 3, "ud": 0.1, "v": 100, "cje": 1_000_000,
                        "t": "2026-07-15 10:00:00",
                    }], endpoint)
                raise AssertionError(endpoint)

        client = Client()
        output = run_screen(client, None, 20)  # type: ignore[arg-type]
        self.assertEqual(client.calls, ["stock_list", "st_list", "all_market"])
        self.assertEqual(len(output["candidates"]), 1)


class PayloadQualityTests(unittest.TestCase):
    def test_valid_bars(self) -> None:
        payload = [
            {"t": "2026-07-14", "o": 10, "h": 11, "l": 9.5, "c": 10.5, "v": 100},
            {"t": "2026-07-15", "o": 10.5, "h": 11.2, "l": 10.1, "c": 11, "v": 120},
        ]
        self.assertEqual(validate_bars(payload)["status"], "pass")

    def test_invalid_bar_relationship(self) -> None:
        report_ = validate_bars([{"t": "2026-07-15", "o": 12, "h": 11, "l": 10, "c": 9, "v": 1}])
        self.assertEqual(report_["status"], "fail")

    def test_limit_pool_duplicate(self) -> None:
        row = {"dm": "sh600000", "p": 10, "zf": 10, "cje": 100}
        self.assertEqual(validate_limit_pool([row, row])["status"], "fail")


class EvidenceGateTests(unittest.TestCase):
    def test_missing_financial_report_caps_score(self) -> None:
        output = evaluate_evidence({
            "code": "600000",
            "cutoff_time": "2026-07-15T15:10:00+08:00",
            "proposed_research_score": 90,
            "evidence": [{
                "category": "filing", "source_url": "https://www.sse.com.cn/example.pdf",
                "available_at": "2026-07-15T10:00:00+08:00", "strength": "primary", "status": "confirmed",
            }],
        })
        self.assertEqual(output["score_cap"], 50)
        self.assertEqual(output["adjusted_research_score"], 50)
        self.assertFalse(output["high_priority_allowed"])

    def test_future_evidence_is_rejected(self) -> None:
        output = evaluate_evidence({
            "cutoff_time": "2026-07-15T15:10:00+08:00",
            "evidence": [{
                "category": "financial_report", "source_url": "https://www.cninfo.com.cn/report.pdf",
                "available_at": "2026-07-16T09:00:00+08:00", "strength": "primary", "status": "confirmed",
            }],
        })
        self.assertEqual(output["coverage_score"], 0)
        self.assertIn("point_in_time.rejected", {flag["code"] for flag in output["flags"]})


class RotationTests(unittest.TestCase):
    def test_accelerating_stage(self) -> None:
        stage, _ = classify(
            {"median_return": 3, "breadth": 0.8, "limit_up_rate": 0.1, "broken_rate": 0, "amount": 120},
            {"median_return": 1, "breadth": 0.6, "amount": 100},
        )
        self.assertEqual(stage, "accelerating")

    def test_analysis_uses_latest_two_dates(self) -> None:
        rows = []
        for date, changes in (("2026-07-14", [-1, 0]), ("2026-07-15", [1, 2])):
            for index, change in enumerate(changes):
                rows.append({"date": date, "code": f"60000{index}", "sector": "测试", "change_pct": change, "amount": 100})
        output = analyze(rows)
        self.assertEqual(output["latest_date"], "2026-07-15")
        self.assertEqual(len(output["sectors"]), 1)


class CacheTests(unittest.TestCase):
    def test_immutable_raw_cache_and_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache = CacheStore(Path(directory))
            first = cache.put("key", "quote", {"p": 10}, 60)
            second = cache.get("key")
            self.assertIsNotNone(second)
            self.assertEqual(first.response_hash, second.response_hash)
            self.assertTrue(second.from_cache)

    def test_endpoint_rendering(self) -> None:
        path, ttl = ZhituClient.render_path("quote", code="000001")
        self.assertEqual(path, "/hs/real/ssjy/000001")
        self.assertGreater(ttl, 0)


class TrackerTests(unittest.TestCase):
    def test_signal_outcome_report(self) -> None:
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        from research_tracker import SCHEMA

        connection.executescript(SCHEMA)
        record_signals(
            connection,
            [{
                "id": "s1", "code": "600000", "signal_date": "2026-07-01",
                "cutoff_time": "2026-07-01T15:10:00+08:00", "signal_price": 10,
                "benchmark": "000300", "benchmark_price": 100,
                "objective": "t1_positive", "score": 70, "ruleset_version": "2.0.0",
            }],
        )
        rows = []
        for day in range(2, 23):
            rows.append({"trade_date": f"2026-07-{day:02d}", "code": "600000", "close": 10 + day / 100, "benchmark": "000300", "benchmark_close": 100})
        record_snapshots(connection, rows)
        self.assertEqual(evaluate(connection), 1)
        groups = report(connection)["groups"]
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["sample_size"], 1)
        self.assertEqual(groups[0]["ruleset_version"], "2.0.0")
        self.assertEqual(groups[0]["sample_status"], "insufficient_sample")

    def test_report_does_not_merge_ruleset_versions(self) -> None:
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        from research_tracker import SCHEMA

        connection.executescript(SCHEMA)
        for version, code in (("2.0.0", "600010"), ("2.1.0", "600011")):
            record_signals(connection, [{
                "id": f"s-{version}", "code": code, "signal_date": "2026-07-01",
                "cutoff_time": "2026-07-01T15:10:00+08:00", "signal_price": 10,
                "objective": "t1_positive", "ruleset_version": version,
            }])
            record_snapshots(connection, [{"trade_date": "2026-07-02", "code": code, "close": 10.2}])
        evaluate(connection)
        groups = report(connection)["groups"]
        self.assertEqual({group["ruleset_version"] for group in groups}, {"2.0.0", "2.1.0"})

    def test_limit_up_requires_observed_high_and_exact_limit_price(self) -> None:
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        from research_tracker import SCHEMA

        connection.executescript(SCHEMA)
        record_signals(connection, [{
            "id": "s2", "code": "600001", "signal_date": "2026-07-01",
            "cutoff_time": "2026-07-01T15:10:00+08:00", "signal_price": 10,
            "objective": "t1_limit_up", "ruleset_version": "2.0.0",
        }])
        record_snapshots(connection, [{"trade_date": "2026-07-02", "code": "600001", "close": 10.2}])
        self.assertEqual(evaluate(connection), 0)
        record_snapshots(connection, [{
            "trade_date": "2026-07-02", "code": "600001", "close": 10.2,
            "high": 11.0, "previous_close": 10.0, "limit_up_price": 11.0,
        }])
        self.assertEqual(evaluate(connection), 1)


if __name__ == "__main__":
    unittest.main()
