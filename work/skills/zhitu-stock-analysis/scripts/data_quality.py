#!/usr/bin/env python3
"""Deterministic validation for core Zhitu payloads.

The module never logs URLs or tokens. It accepts saved JSON from a file/stdin and
returns a machine-readable quality report suitable for a hard gate before scoring.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


PRICE_TOLERANCE = 0.011
PERCENTAGE_POINT_TOLERANCE = 0.05


@dataclass(frozen=True)
class Issue:
    severity: str
    code: str
    message: str


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _date(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _unwrap_quote(payload: Any) -> dict[str, Any] | None:
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, dict):
            return data
        if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict):
            return data[0]
        return payload
    if isinstance(payload, list) and len(payload) == 1 and isinstance(payload[0], dict):
        return payload[0]
    return None


def _report(kind: str, issues: Iterable[Issue], metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    issue_list = list(issues)
    penalty = sum(25 if item.severity == "error" else 6 for item in issue_list)
    score = max(0, 100 - penalty)
    hard_fail = any(item.severity == "error" for item in issue_list)
    if hard_fail or score < 60:
        status = "fail"
    elif score < 90:
        status = "warn"
    else:
        status = "pass"
    return {
        "kind": kind,
        "quality_score": score,
        "status": status,
        "allow_stock_scoring": not hard_fail and score >= 80,
        "issues": [asdict(item) for item in issue_list],
        "metrics": metrics or {},
    }


def validate_quote(payload: Any) -> dict[str, Any]:
    quote = _unwrap_quote(payload)
    if quote is None:
        return _report("quote", [Issue("error", "quote.shape", "Expected one quote object")])

    issues: list[Issue] = []
    required = ("p", "yc", "o", "h", "l", "pc", "zf", "ud", "v", "cje", "t")
    for field in required:
        if field not in quote or quote[field] is None:
            issues.append(Issue("error", f"quote.missing.{field}", f"Missing required field {field}"))

    p, previous = _number(quote.get("p")), _number(quote.get("yc"))
    open_, high, low = (_number(quote.get(key)) for key in ("o", "h", "l"))
    change, change_pct = _number(quote.get("ud")), _number(quote.get("pc"))
    amplitude = _number(quote.get("zf"))

    if p is not None and p <= 0:
        issues.append(Issue("error", "quote.price.nonpositive", "Latest price must be positive"))
    if previous is not None and previous <= 0:
        issues.append(Issue("error", "quote.previous.nonpositive", "Previous close must be positive"))
    no_intraday_trade = all(value == 0 for value in (open_, high, low) if value is not None) and all(
        value is not None for value in (open_, high, low)
    )
    if no_intraday_trade:
        issues.append(Issue("warn", "quote.no_intraday_trade", "Open/high/low are zero; check pre-open or suspension state"))
    if not no_intraday_trade and all(value is not None for value in (low, high)) and low > high:
        issues.append(Issue("error", "quote.range.invalid", "Low is greater than high"))
    if not no_intraday_trade and all(value is not None for value in (p, low, high)) and not low - PRICE_TOLERANCE <= p <= high + PRICE_TOLERANCE:
        issues.append(Issue("error", "quote.price.outside_range", "Latest price is outside low/high"))
    if not no_intraday_trade and all(value is not None for value in (open_, low, high)) and not low - PRICE_TOLERANCE <= open_ <= high + PRICE_TOLERANCE:
        issues.append(Issue("error", "quote.open.outside_range", "Open is outside low/high"))

    expected_change = None
    expected_pct = None
    if p is not None and previous is not None and previous > 0:
        expected_change = p - previous
        expected_pct = expected_change / previous * 100
        if change is not None and abs(change - expected_change) > PRICE_TOLERANCE:
            issues.append(Issue("error", "quote.change.mismatch", "Price change does not match latest minus previous close"))
        if change_pct is not None and abs(change_pct - expected_pct) > PERCENTAGE_POINT_TOLERANCE:
            issues.append(Issue("error", "quote.change_pct.mismatch", "Change percentage does not match price and previous close"))
        if not no_intraday_trade and amplitude is not None and high is not None and low is not None:
            expected_amplitude = (high - low) / previous * 100
            if abs(amplitude - expected_amplitude) > PERCENTAGE_POINT_TOLERANCE:
                issues.append(Issue("error", "quote.amplitude.mismatch", "Amplitude does not match high, low, and previous close"))

    for field in ("v", "cje", "hs", "lt", "sz"):
        value = _number(quote.get(field))
        if value is not None and value < 0:
            issues.append(Issue("error", f"quote.negative.{field}", f"{field} must not be negative"))

    source_time = _date(quote.get("t"))
    if quote.get("t") is not None and source_time is None:
        issues.append(Issue("warn", "quote.time.invalid", "Unrecognized quote timestamp"))

    return _report(
        "quote",
        issues,
        {
            "source_time": source_time.isoformat(sep=" ") if source_time else None,
            "expected_change": round(expected_change, 4) if expected_change is not None else None,
            "expected_change_pct": round(expected_pct, 4) if expected_pct is not None else None,
        },
    )


def validate_stock_list(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, list) or not payload:
        return _report("stock_list", [Issue("error", "stock_list.shape", "Expected a non-empty list")])

    issues: list[Issue] = []
    seen: set[str] = set()
    duplicate_count = 0
    invalid_count = 0
    for index, row in enumerate(payload):
        if not isinstance(row, dict):
            invalid_count += 1
            issues.append(Issue("error", "stock_list.row_type", f"Row {index} is not an object"))
            continue
        code = str(row.get("dm", "")).strip()
        name = str(row.get("mc", "")).strip()
        exchange = str(row.get("jys", "")).lower().strip()
        if not re.fullmatch(r"\d{6}", code) or not name or exchange not in {"sh", "sz"}:
            invalid_count += 1
            issues.append(Issue("error", "stock_list.invalid_row", f"Invalid stock-list row at index {index}"))
        if code in seen:
            duplicate_count += 1
            issues.append(Issue("error", "stock_list.duplicate", f"Duplicate code {code}"))
        seen.add(code)

    return _report(
        "stock_list",
        issues,
        {"records": len(payload), "unique_codes": len(seen), "duplicates": duplicate_count, "invalid_rows": invalid_count},
    )


def validate_financial_ratios(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, list) or not payload:
        return _report("financial_ratios", [Issue("error", "financial.shape", "Expected a non-empty list")])

    issues: list[Issue] = []
    periods: set[str] = set()
    numeric_fields = 0
    for index, row in enumerate(payload):
        if not isinstance(row, dict):
            issues.append(Issue("error", "financial.row_type", f"Row {index} is not an object"))
            continue
        period_text = str(row.get("jzrq", "")).strip()
        disclosure_text = str(row.get("plrq", "")).strip()
        period = _date(period_text)
        disclosure = _date(disclosure_text)
        if period is None:
            issues.append(Issue("error", "financial.period.invalid", f"Invalid period at row {index}"))
        if disclosure_text and disclosure is None:
            issues.append(Issue("warn", "financial.disclosure.invalid", f"Invalid disclosure date at row {index}"))
        if period and disclosure and disclosure < period:
            issues.append(Issue("error", "financial.disclosure.before_period", f"Disclosure precedes period at row {index}"))
        if period_text in periods:
            issues.append(Issue("error", "financial.period.duplicate", f"Duplicate reporting period {period_text}"))
        periods.add(period_text)

        for key, value in row.items():
            if key in {"jzrq", "plrq"} or value is None:
                continue
            if isinstance(value, bool):
                issues.append(Issue("warn", "financial.boolean_numeric", f"Unexpected boolean in {key} at row {index}"))
            elif _number(value) is not None:
                numeric_fields += 1

    if numeric_fields == 0:
        issues.append(Issue("error", "financial.no_numeric_values", "No numeric financial metrics found"))

    return _report(
        "financial_ratios",
        issues,
        {"records": len(payload), "periods": len(periods), "numeric_values": numeric_fields},
    )


def _unwrap_list(payload: Any) -> list[dict[str, Any]] | None:
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        payload = payload["data"]
    if isinstance(payload, list) and all(isinstance(row, dict) for row in payload):
        return payload
    return None


def validate_bars(payload: Any) -> dict[str, Any]:
    rows = _unwrap_list(payload)
    if not rows:
        return _report("bars", [Issue("error", "bars.shape", "Expected a non-empty list of bar objects")])
    issues: list[Issue] = []
    timestamps: set[str] = set()
    previous_time: datetime | None = None
    for index, row in enumerate(rows):
        time_text = str(row.get("t") or row.get("date") or row.get("d") or "").strip()
        source_time = _date(time_text)
        if source_time is None:
            issues.append(Issue("error", "bars.time.invalid", f"Invalid timestamp at row {index}"))
        elif time_text in timestamps:
            issues.append(Issue("error", "bars.time.duplicate", f"Duplicate timestamp {time_text}"))
        elif previous_time and source_time < previous_time:
            issues.append(Issue("warn", "bars.order.descending", "Bars are not in ascending time order"))
        if source_time:
            previous_time = source_time
        timestamps.add(time_text)

        open_ = _number(row.get("o"))
        high = _number(row.get("h"))
        low = _number(row.get("l"))
        close = _number(row.get("c") if row.get("c") is not None else row.get("p"))
        if any(value is None for value in (open_, high, low, close)):
            issues.append(Issue("error", "bars.ohlc.missing", f"Missing/non-numeric OHLC at row {index}"))
        elif low > high or not low - PRICE_TOLERANCE <= open_ <= high + PRICE_TOLERANCE or not low - PRICE_TOLERANCE <= close <= high + PRICE_TOLERANCE:
            issues.append(Issue("error", "bars.ohlc.invalid", f"Invalid OHLC relationship at row {index}"))
        for field in ("v", "cje"):
            value = _number(row.get(field))
            if value is not None and value < 0:
                issues.append(Issue("error", f"bars.negative.{field}", f"Negative {field} at row {index}"))
    return _report("bars", issues, {"records": len(rows), "unique_timestamps": len(timestamps)})


def validate_limit_pool(payload: Any) -> dict[str, Any]:
    rows = _unwrap_list(payload)
    if rows is None:
        return _report("limit_pool", [Issue("error", "pool.shape", "Expected a list of pool objects")])
    issues: list[Issue] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        code = str(row.get("dm", "")).lower().replace("sh", "").replace("sz", "")
        if not re.fullmatch(r"\d{6}", code):
            issues.append(Issue("error", "pool.code.invalid", f"Invalid code at row {index}"))
        if code in seen:
            issues.append(Issue("error", "pool.code.duplicate", f"Duplicate code {code}"))
        seen.add(code)
        price = _number(row.get("p"))
        change_pct = _number(row.get("zf") if row.get("zf") is not None else row.get("pc"))
        if price is None or price <= 0:
            issues.append(Issue("error", "pool.price.invalid", f"Invalid price at row {index}"))
        if change_pct is None:
            issues.append(Issue("warn", "pool.change_pct.missing", f"Missing change percentage at row {index}"))
        for field in ("cje", "lt", "zsz", "zj", "zbc", "lbc"):
            value = _number(row.get(field))
            if value is not None and value < 0:
                issues.append(Issue("error", f"pool.negative.{field}", f"Negative {field} at row {index}"))
    return _report("limit_pool", issues, {"records": len(rows), "unique_codes": len(seen)})


VALIDATORS = {
    "bars": validate_bars,
    "quote": validate_quote,
    "stock-list": validate_stock_list,
    "financial-ratios": validate_financial_ratios,
    "limit-pool": validate_limit_pool,
}


def load_json(path: str) -> Any:
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a saved Zhitu JSON payload")
    parser.add_argument("kind", choices=sorted(VALIDATORS))
    parser.add_argument("input", help="JSON file path or - for stdin")
    args = parser.parse_args()

    report = VALIDATORS[args.kind](load_json(args.input))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
