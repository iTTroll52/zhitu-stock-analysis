#!/usr/bin/env python3
"""Deterministic Shanghai/Shenzhen main-board market-data pre-screen."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

from data_quality import validate_quote, validate_stock_list
from zhitu_client import ZhituClient, ZhituError


MAIN_BOARD_PREFIXES = ("600", "601", "603", "605", "000", "001", "002", "003")
EXCLUDED_PREFIXES = ("300", "301", "688", "689")


def number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def normalize_code(value: Any) -> str:
    match = re.search(r"(\d{6})", str(value or ""))
    return match.group(1) if match else ""


def eligibility(code: str, name: str, st_codes: set[str]) -> tuple[bool, str]:
    normalized_name = name.upper().replace(" ", "")
    if code in st_codes or "ST" in normalized_name or "退" in normalized_name:
        return False, "ST/*ST/退市风险"
    if code.startswith(EXCLUDED_PREFIXES):
        return False, "非沪深主板权限范围"
    if not code.startswith(MAIN_BOARD_PREFIXES):
        return False, "无法确认属于沪深主板"
    return True, "eligible"


def _bucket(value: float | None, thresholds: list[tuple[float, float]], missing: float = 0.0) -> float:
    if value is None:
        return missing
    score = 0.0
    for threshold, points in thresholds:
        if value >= threshold:
            score = points
    return score


def score_market_record(row: dict[str, Any]) -> dict[str, Any]:
    """Return a reproducible pre-screen score; never interpret it as return probability."""
    amount = number(row.get("cje"))
    change_pct = number(row.get("pc"))
    turnover = number(row.get("hs"))
    latest = number(row.get("p"))
    open_ = number(row.get("o"))
    previous = number(row.get("yc"))
    amplitude = number(row.get("zf"))
    pe = number(row.get("pe"))

    liquidity = _bucket(amount, [(20e6, 4), (50e6, 8), (100e6, 12), (300e6, 16), (800e6, 20)])
    relative_strength = _bucket(change_pct, [(-3, 2), (-1, 5), (0, 9), (1, 13), (3, 17), (6, 20)])
    turnover_score = _bucket(turnover, [(0.5, 3), (1, 6), (2, 10), (4, 13), (8, 15)])
    if turnover is not None and turnover > 25:
        turnover_score = 8

    intraday = 0.0
    if latest is not None and previous and latest >= previous:
        intraday += 7.5
    if latest is not None and open_ and latest >= open_:
        intraday += 7.5

    volatility = 0.0
    if amplitude is not None:
        volatility = 10 if 1 <= amplitude <= 6 else 7 if amplitude <= 9 else 3

    valuation_quality = 0.0
    if pe is not None:
        valuation_quality = 10 if 0 < pe <= 40 else 7 if 40 < pe <= 80 else 2

    limit_structure = 0.0
    if change_pct is not None:
        limit_structure = 10 if 9.5 <= change_pct <= 11 else 6 if change_pct >= 6 else 3 if change_pct >= 3 else 0

    components = {
        "liquidity_20": liquidity,
        "relative_strength_20": relative_strength,
        "turnover_15": turnover_score,
        "intraday_strength_15": intraday,
        "volatility_quality_10": volatility,
        "valuation_quality_10": valuation_quality,
        "limit_structure_10": limit_structure,
    }
    return {
        "pre_screen_score": round(sum(components.values()), 2),
        "components": components,
        "label": "short-term market-data pre-screen; pending catalyst and primary-source validation",
    }


def _rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        payload = payload["data"]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        return [payload]
    return []


def run_screen(client: ZhituClient, codes: list[str] | None, top: int) -> dict[str, Any]:
    universe_result = client.get("stock_list")
    st_result = client.get("st_list")
    universe = _rows(universe_result.payload)
    st_rows = _rows(st_result.payload)
    universe_quality = validate_stock_list(universe)
    st_quality = validate_stock_list(st_rows) if st_rows else {"status": "warn", "quality_score": 80, "issues": []}
    if universe_quality["status"] == "fail":
        raise ValueError("Stock universe failed deterministic validation")

    names = {normalize_code(row.get("dm")): str(row.get("mc", "")) for row in universe}
    st_codes = {normalize_code(row.get("dm")) for row in st_rows}
    requested = [normalize_code(code) for code in codes] if codes is not None else list(names)
    requested = list(dict.fromkeys(code for code in requested if code))
    excluded: list[dict[str, str]] = []
    eligible: list[str] = []
    for code in requested:
        ok, reason = eligibility(code, names.get(code, ""), st_codes)
        if ok:
            eligible.append(code)
        else:
            excluded.append({"code": code, "name": names.get(code, ""), "reason": reason})

    candidates: list[dict[str, Any]] = []
    market_rows: dict[str, tuple[dict[str, Any], Any]] = {}
    if codes is None:
        all_market = client.get("all_market")
        for row in _rows(all_market.payload):
            code = normalize_code(row.get("dm") or row.get("code"))
            if code:
                market_rows[code] = (row, all_market)

    for code in eligible:
        if codes is None:
            pair = market_rows.get(code)
            if pair is None:
                excluded.append({"code": code, "name": names.get(code, ""), "reason": "全市场快照缺少该证券"})
                continue
            row, result = pair
        else:
            result = client.get("quote", code=code)
            rows = _rows(result.payload)
            if not rows:
                excluded.append({"code": code, "name": names.get(code, ""), "reason": "实时行情为空"})
                continue
            row = rows[0]
        quality = validate_quote(row)
        if not quality["allow_stock_scoring"]:
            excluded.append({"code": code, "name": names.get(code, ""), "reason": "行情质量闸门未通过"})
            continue
        scored = score_market_record(row)
        candidates.append(
            {
                "code": code,
                "name": names.get(code, ""),
                **scored,
                "quality_score": quality["quality_score"],
                "source_time": quality["metrics"].get("source_time"),
                "lineage": result.lineage(),
            }
        )

    candidates.sort(key=lambda item: (-item["pre_screen_score"], item["code"]))
    return {
        "schema_version": "2.0.0",
        "objective": "short-term research-priority pre-screen, not return probability",
        "universe_quality": universe_quality,
        "st_list_quality": st_quality,
        "requested": len(requested),
        "eligible": len(eligible),
        "candidates": candidates[:top],
        "excluded": excluded,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Screen eligible main-board A-shares")
    parser.add_argument("--codes", nargs="*", help="Six-digit codes; omit only when intentionally screening the full universe")
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = run_screen(ZhituClient(), args.codes, max(1, args.top))
    except (ZhituError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
