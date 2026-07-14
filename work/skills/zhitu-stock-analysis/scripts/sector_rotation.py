#!/usr/bin/env python3
"""Aggregate point-in-time stock snapshots into deterministic sector stages."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def summarize(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        sector = str(row.get("sector", "")).strip()
        if sector:
            groups[sector].append(row)

    output: dict[str, dict[str, float]] = {}
    for sector, members in groups.items():
        returns = [value for row in members if (value := _number(row.get("change_pct"))) is not None]
        amounts = [value for row in members if (value := _number(row.get("amount"))) is not None and value >= 0]
        if not returns:
            continue
        up_count = sum(value > 0 for value in returns)
        limit_up_count = sum(bool(row.get("limit_up")) for row in members)
        broken_count = sum(bool(row.get("broken_limit")) for row in members)
        output[sector] = {
            "members": float(len(members)),
            "median_return": statistics.median(returns),
            "breadth": up_count / len(returns),
            "limit_up_rate": limit_up_count / len(members),
            "broken_rate": broken_count / len(members),
            "amount": sum(amounts),
        }
    return output


def classify(current: dict[str, float], previous: dict[str, float] | None) -> tuple[str, list[str]]:
    previous = previous or {"median_return": 0.0, "breadth": 0.5, "amount": 0.0}
    ret = current["median_return"]
    breadth = current["breadth"]
    limit_rate = current["limit_up_rate"]
    broken_rate = current["broken_rate"]
    previous_ret = previous.get("median_return", 0.0)
    previous_breadth = previous.get("breadth", 0.5)
    previous_amount = previous.get("amount", 0.0)
    amount_ratio = current["amount"] / previous_amount if previous_amount > 0 else None
    evidence = [f"median_return={ret:.2f}%", f"breadth={breadth:.1%}", f"limit_up_rate={limit_rate:.1%}"]
    if amount_ratio is not None:
        evidence.append(f"amount_ratio={amount_ratio:.2f}")

    if ret >= 2 and breadth >= 0.65 and limit_rate >= 0.05 and (amount_ratio is None or amount_ratio >= 1.10):
        stage = "accelerating"
    elif ret >= 1 and breadth >= 0.58 and ret > previous_ret and (amount_ratio is None or amount_ratio >= 1.0):
        stage = "strengthening"
    elif ret >= 0.5 and breadth >= 0.55 and previous_ret < 0.5:
        stage = "starting"
    elif ret > 0 and (breadth < 0.48 or broken_rate >= limit_rate > 0 or ret < previous_ret - 0.8):
        stage = "diverging"
    elif ret <= 0 and (previous_ret > 0.5 or breadth < 0.4 or breadth < previous_breadth - 0.15):
        stage = "fading"
    elif ret >= 0.5 and previous_ret <= 0:
        stage = "rebounding"
    else:
        stage = "watch"
    return stage, evidence


def analyze(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in snapshots:
        date = str(row.get("date", "")).strip()
        if date:
            by_date[date].append(row)
    dates = sorted(by_date)
    if not dates:
        raise ValueError("No dated snapshots")
    latest_date = dates[-1]
    previous_date = dates[-2] if len(dates) > 1 else None
    latest = summarize(by_date[latest_date])
    previous = summarize(by_date[previous_date]) if previous_date else {}
    sectors = []
    for sector, metrics in latest.items():
        stage, evidence = classify(metrics, previous.get(sector))
        sectors.append({"sector": sector, "stage": stage, "metrics": metrics, "evidence": evidence})
    stage_rank = {"accelerating": 0, "strengthening": 1, "starting": 2, "rebounding": 3, "diverging": 4, "watch": 5, "fading": 6}
    sectors.sort(key=lambda row: (stage_rank[row["stage"]], -row["metrics"]["median_return"], row["sector"]))
    return {
        "schema_version": "2.0.0",
        "latest_date": latest_date,
        "previous_date": previous_date,
        "method": "equal-member median return + breadth + limit structure + comparable snapshot amount",
        "sectors": sectors,
        "limitations": [
            "Requires point-in-time sector membership supplied in each row",
            "Stage is a descriptive rule, not a forecast probability",
            "Compare the same market-time cutoff across dates",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify sector rotation from normalized snapshots")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8-sig"))
    rows = payload.get("snapshots", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise SystemExit("Expected a JSON list or {snapshots: [...]} object")
    report = analyze(rows)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
