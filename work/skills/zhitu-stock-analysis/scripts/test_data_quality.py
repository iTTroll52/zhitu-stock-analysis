#!/usr/bin/env python3

from __future__ import annotations

import unittest

from data_quality import validate_financial_ratios, validate_quote, validate_stock_list


class DataQualityTests(unittest.TestCase):
    def test_valid_quote_passes(self) -> None:
        report = validate_quote(
            {
                "p": 10.10,
                "yc": 10.00,
                "o": 10.00,
                "h": 10.20,
                "l": 9.95,
                "pc": 1.0,
                "zf": 2.5,
                "ud": 0.10,
                "v": 1000,
                "cje": 10050,
                "hs": 0.5,
                "lt": 1_000_000,
                "sz": 2_000_000,
                "t": "2026-07-15 10:00:00",
            }
        )
        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["allow_stock_scoring"])

    def test_inconsistent_quote_fails(self) -> None:
        report = validate_quote(
            {
                "p": 11.00,
                "yc": 10.00,
                "o": 10.00,
                "h": 10.50,
                "l": 9.90,
                "pc": 1.0,
                "zf": 6.0,
                "ud": 0.10,
                "v": -1,
                "cje": 100,
                "t": "2026-07-15 10:00:00",
            }
        )
        self.assertEqual(report["status"], "fail")
        self.assertFalse(report["allow_stock_scoring"])
        codes = {item["code"] for item in report["issues"]}
        self.assertIn("quote.price.outside_range", codes)
        self.assertIn("quote.change_pct.mismatch", codes)

    def test_stock_list_detects_duplicates(self) -> None:
        report = validate_stock_list(
            [
                {"dm": "000001", "mc": "平安银行", "jys": "sz"},
                {"dm": "000001", "mc": "平安银行", "jys": "sz"},
            ]
        )
        self.assertEqual(report["status"], "fail")

    def test_financial_ratios_pass(self) -> None:
        report = validate_financial_ratios(
            [{"jzrq": "2026-03-31", "plrq": "2026-04-25", "jzcsyl": 8.1, "zcfzl": 41.2}]
        )
        self.assertEqual(report["status"], "pass")

    def test_financial_disclosure_before_period_fails(self) -> None:
        report = validate_financial_ratios(
            [{"jzrq": "2026-03-31", "plrq": "2026-03-01", "jzcsyl": 8.1}]
        )
        self.assertEqual(report["status"], "fail")


if __name__ == "__main__":
    unittest.main()
