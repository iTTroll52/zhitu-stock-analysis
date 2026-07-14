#!/usr/bin/env python3
"""Detect bottom-launch, acceleration, limit-up, and consecutive-limit signals.

Signals are deterministic research labels, not return probabilities. Input must
already pass the main-board/ST gate and preserve point-in-time data.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any


SIGNAL_PRIORITY = ("consecutive_limit_up", "limit_up", "accelerating", "bottom_start")
FAVORABLE_BOTTOM_STAGES = {"starting", "strengthening", "rebounding"}
FAVORABLE_ACCELERATION_STAGES = {"strengthening", "accelerating"}
HOSTILE_MARKETS = {"fading", "panic", "high_uncertainty"}


def number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def moving_average(values: list[float], length: int) -> float | None:
    return statistics.fmean(values[-length:]) if len(values) >= length else None


def _time_minutes(value: Any) -> int | None:
    text = str(value or "").strip()
    parts = text.split(":")
    if len(parts) < 2:
        return None
    try:
        return int(parts[0]) * 60 + int(parts[1])
    except ValueError:
        return None


def _bar_close(row: dict[str, Any]) -> float | None:
    return number(row.get("c") if row.get("c") is not None else row.get("p"))


def _bar_volume(row: dict[str, Any]) -> float | None:
    return number(row.get("v"))


def _business_points(candidate: dict[str, Any]) -> tuple[float, list[str]]:
    support = str(candidate.get("business_support", "unverified")).lower()
    evidence_score = number(candidate.get("evidence_score")) or 0
    reasons: list[str] = []
    points = 10 if support == "confirmed" else 5 if support == "partial" else 0
    if support in {"confirmed", "partial"}:
        reasons.append(f"business_support={support}")
    if evidence_score < 50:
        reasons.append("primary evidence below priority threshold")
    return points, reasons


def calculate_features(candidate: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    bars = candidate.get("bars", [])
    quote = candidate.get("quote", {})
    if not isinstance(bars, list) or not isinstance(quote, dict):
        return {}, ["bars/quote shape invalid"]
    clean_bars = [row for row in bars if isinstance(row, dict)]
    closes = [value for row in clean_bars if (value := _bar_close(row)) is not None]
    highs = [value for row in clean_bars[-20:] if (value := number(row.get("h"))) is not None]
    lows = [value for row in clean_bars[-20:] if (value := number(row.get("l"))) is not None]
    volumes = [value for row in clean_bars if (value := _bar_volume(row)) is not None and value >= 0]
    warnings: list[str] = []
    if len(closes) < 20 or len(highs) < 20 or len(lows) < 20:
        warnings.append("requires at least 20 complete point-in-time daily bars")
        return {}, warnings

    latest = number(quote.get("p")) or closes[-1]
    previous = number(quote.get("yc")) or (closes[-2] if len(closes) >= 2 else None)
    change_pct = number(quote.get("pc"))
    if change_pct is None and previous:
        change_pct = (latest / previous - 1) * 100
    high20, low20 = max(highs), min(lows)
    range_position = (latest - low20) / (high20 - low20) if high20 > low20 else 0.5
    ma5, ma10, ma20 = (moving_average(closes, length) for length in (5, 10, 20))
    prior_ma5 = statistics.fmean(closes[-6:-1]) if len(closes) >= 6 else None
    recent_returns = [
        (closes[index] / closes[index - 1] - 1) * 100
        for index in range(max(1, len(closes) - 3), len(closes))
        if closes[index - 1] > 0
    ]

    volume_ratio = number(candidate.get("comparable_volume_ratio"))
    volume_ratio_source = "comparable_same_time"
    if volume_ratio is None:
        volume_ratio = number(quote.get("lb"))
        volume_ratio_source = "vendor_volume_ratio"
    if volume_ratio is None and len(volumes) >= 6:
        baseline = statistics.median(volumes[-6:-1])
        volume_ratio = volumes[-1] / baseline if baseline > 0 else None
        volume_ratio_source = "daily_volume_median"
    if volume_ratio is None:
        warnings.append("volume ratio unavailable")

    pool = candidate.get("pool", {}) if isinstance(candidate.get("pool", {}), dict) else {}
    limit_up_price = number(pool.get("limit_up_price") or candidate.get("limit_up_price"))
    if limit_up_price is None and pool.get("is_limit_up"):
        limit_up_price = number(pool.get("p"))
    open_, high, low = (number(quote.get(key)) for key in ("o", "h", "l"))
    touched_limit = bool(pool.get("is_limit_up")) or (
        high is not None and limit_up_price is not None and high >= limit_up_price - 0.001
    )
    one_word = bool(
        limit_up_price is not None
        and all(value is not None and abs(value - limit_up_price) <= 0.001 for value in (open_, high, low, latest))
    )
    amount = number(quote.get("cje")) or number(pool.get("cje"))
    seal_amount = number(pool.get("zj"))
    seal_ratio = seal_amount / amount if seal_amount is not None and amount and amount > 0 else None

    return {
        "latest": latest,
        "change_pct": change_pct,
        "ma5": ma5,
        "ma10": ma10,
        "ma20": ma20,
        "prior_ma5": prior_ma5,
        "range_position_20d": range_position,
        "drawdown_from_20d_high_pct": (latest / high20 - 1) * 100 if high20 else None,
        "recent_returns": recent_returns,
        "volume_ratio": volume_ratio,
        "volume_ratio_source": volume_ratio_source,
        "turnover": number(quote.get("hs")),
        "sector_stage": str(candidate.get("sector_stage", "watch")),
        "market_regime": str(candidate.get("market_regime", "unknown")),
        "touched_limit": touched_limit,
        "limit_up_price": limit_up_price,
        "one_word": one_word,
        "consecutive_boards": int(number(pool.get("lbc")) or 0),
        "first_seal_minutes": _time_minutes(pool.get("fbt")),
        "last_seal_minutes": _time_minutes(pool.get("lbt")),
        "break_count": int(number(pool.get("zbc")) or 0),
        "seal_ratio": seal_ratio,
    }, warnings


def detect_bottom_start(candidate: dict[str, Any], features: dict[str, Any]) -> dict[str, Any]:
    business, business_reasons = _business_points(candidate)
    stage = features["sector_stage"]
    change = features["change_pct"]
    volume_ratio = features["volume_ratio"]
    range_position = features["range_position_20d"]
    turn_up = features["ma5"] is not None and features["prior_ma5"] is not None and features["ma5"] > features["prior_ma5"]
    above_ma5 = features["latest"] >= features["ma5"]
    conditions = {
        "bottom_zone": range_position <= 0.45,
        "ma5_turning_up": turn_up,
        "price_above_ma5": above_ma5,
        "controlled_positive_move": change is not None and 0.5 <= change <= 7,
        "volume_confirmation": volume_ratio is not None and 1.2 <= volume_ratio <= 3.5,
        "sector_confirmation": stage in FAVORABLE_BOTTOM_STAGES,
    }
    score = 0.0
    score += 25 if range_position <= 0.25 else 18 if range_position <= 0.45 else 0
    score += 20 if turn_up and above_ma5 else 10 if above_ma5 else 0
    score += 15 if volume_ratio is not None and 1.2 <= volume_ratio <= 2.5 else 8 if volume_ratio is not None and volume_ratio <= 3.5 else 0
    score += 15 if change is not None and 1 <= change <= 5 else 8 if change is not None and 0 < change <= 7 else 0
    score += 15 if stage in FAVORABLE_BOTTOM_STAGES else 0
    score += business
    matched = all(conditions.values()) and score >= 65
    return {"matched": matched, "score": round(score, 2), "conditions": conditions, "evidence": business_reasons}


def detect_accelerating(candidate: dict[str, Any], features: dict[str, Any]) -> dict[str, Any]:
    business, business_reasons = _business_points(candidate)
    stage = features["sector_stage"]
    change = features["change_pct"]
    volume_ratio = features["volume_ratio"]
    returns = features["recent_returns"]
    aligned = features["latest"] > features["ma5"] > features["ma10"] > features["ma20"]
    momentum = len(returns) >= 2 and returns[-1] > 0 and sum(returns[-3:]) > 2
    conditions = {
        "ma_alignment": aligned,
        "positive_momentum": momentum,
        "near_20d_strength_zone": features["range_position_20d"] >= 0.65,
        "controlled_acceleration": change is not None and 1.5 <= change <= 8,
        "volume_confirmation": volume_ratio is not None and 1.2 <= volume_ratio <= 3.5,
        "sector_confirmation": stage in FAVORABLE_ACCELERATION_STAGES,
    }
    score = 20 if aligned else 0
    score += 20 if momentum else 0
    score += 10 if features["range_position_20d"] >= 0.75 else 6 if features["range_position_20d"] >= 0.65 else 0
    score += 15 if volume_ratio is not None and 1.2 <= volume_ratio <= 2.5 else 8 if volume_ratio is not None and volume_ratio <= 3.5 else 0
    score += 15 if change is not None and 2 <= change <= 6 else 8 if change is not None and change <= 8 else 0
    score += 10 if stage in FAVORABLE_ACCELERATION_STAGES else 0
    score += business
    matched = all(conditions.values()) and score >= 70
    return {"matched": matched, "score": round(score, 2), "conditions": conditions, "evidence": business_reasons}


def detect_limit_structure(candidate: dict[str, Any], features: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    business, business_reasons = _business_points(candidate)
    stage = features["sector_stage"]
    board_count = features["consecutive_boards"]
    first_seal = features["first_seal_minutes"]
    breaks = features["break_count"]
    seal_ratio = features["seal_ratio"]
    turnover = features["turnover"]
    score = 0.0
    score += 20 if stage in FAVORABLE_ACCELERATION_STAGES else 12 if stage in FAVORABLE_BOTTOM_STAGES else 0
    score += 20 if first_seal is not None and first_seal <= 600 else 14 if first_seal is not None and first_seal <= 660 else 6 if first_seal is not None else 0
    score += 15 if breaks <= 1 else 8 if breaks <= 3 else 0
    score += 15 if seal_ratio is not None and seal_ratio >= 0.10 else 8 if seal_ratio is not None and seal_ratio >= 0.03 else 0
    score += 10 if turnover is not None and 2 <= turnover <= 15 else 5 if turnover is not None and turnover <= 25 else 0
    score += 10 if 1 <= board_count <= 3 else 5 if board_count == 0 else 0
    score += business
    no_chase: list[str] = []
    if features["one_word"]:
        no_chase.append("one-word limit; normal buy availability is unverified")
    if breaks >= 5:
        no_chase.append("break count is high")
    if turnover is not None and turnover > 25:
        no_chase.append("turnover is extremely high")
    if board_count >= 4:
        no_chase.append("high consecutive-board position")
    if candidate.get("evidence_score") is None or (number(candidate.get("evidence_score")) or 0) < 50:
        no_chase.append("company evidence is insufficient for priority tier")
    common = {
        "score": round(score, 2),
        "conditions": {
            "exact_limit_price_available": features["limit_up_price"] is not None,
            "touched_limit": features["touched_limit"],
            "sector_not_fading": stage != "fading",
        },
        "no_chase_flags": no_chase,
        "evidence": business_reasons,
    }
    limit_signal = {**common, "matched": features["touched_limit"] and features["limit_up_price"] is not None and stage != "fading" and score >= 55}
    consecutive = {**common, "matched": limit_signal["matched"] and board_count >= 2, "board_count": board_count}
    return limit_signal, consecutive


def analyze_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    quality_score = number(candidate.get("quality_score"))
    if quality_score is None or quality_score < 80:
        return {
            "code": candidate.get("code"),
            "name": candidate.get("name"),
            "eligible_for_signals": False,
            "exclusion_reason": "data quality below 80 or missing",
            "matched_signals": [],
        }
    features, warnings = calculate_features(candidate)
    if not features:
        return {
            "code": candidate.get("code"),
            "name": candidate.get("name"),
            "eligible_for_signals": False,
            "exclusion_reason": "; ".join(warnings),
            "matched_signals": [],
        }

    bottom = detect_bottom_start(candidate, features)
    accelerating = detect_accelerating(candidate, features)
    limit_up, consecutive = detect_limit_structure(candidate, features)
    signals = {
        "bottom_start": bottom,
        "accelerating": accelerating,
        "limit_up": limit_up,
        "consecutive_limit_up": consecutive,
    }
    matched = [name for name in SIGNAL_PRIORITY if signals[name]["matched"]]
    primary = matched[0] if matched else None
    evidence_score = number(candidate.get("evidence_score")) or 0
    business_support = str(candidate.get("business_support", "unverified")).lower()
    validation_status = str(candidate.get("strategy_validation_status", "experimental")).lower()
    validated = validation_status in {"validated", "out_of_sample_validated"}
    hostile = features["market_regime"] in HOSTILE_MARKETS
    priority_allowed = bool(
        primary
        and evidence_score >= 50
        and business_support in {"confirmed", "partial"}
        and not hostile
        and validated
    )
    all_no_chase = list(limit_up.get("no_chase_flags", []))
    if hostile:
        all_no_chase.append(f"hostile market regime: {features['market_regime']}")
    if features["volume_ratio"] is not None and features["volume_ratio"] > 3.5:
        all_no_chase.append("volume expansion may indicate climax rather than launch")
    if primary and not validated:
        all_no_chase.append(f"ruleset is not out-of-sample validated: {validation_status}")
    if priority_allowed and not all_no_chase:
        research_tier = "priority"
    elif primary and not validated:
        research_tier = "experimental_watch"
    else:
        research_tier = "watch_only"
    return {
        "code": candidate.get("code"),
        "name": candidate.get("name"),
        "sector": candidate.get("sector"),
        "eligible_for_signals": True,
        "primary_signal": primary,
        "matched_signals": matched,
        "strategy_validation_status": validation_status,
        "research_tier": research_tier,
        "signal_score": signals[primary]["score"] if primary else 0,
        "signals": signals,
        "features": features,
        "warnings": warnings,
        "no_chase_flags": list(dict.fromkeys(all_no_chase)),
        "invalidation": [
            "sector stage weakens to diverging/fading",
            "price loses the event or launch structure on expanding volume",
            "catalyst, earnings, order, or capacity evidence is contradicted",
        ],
    }


def analyze(payload: dict[str, Any], top: int = 5) -> dict[str, Any]:
    candidates = payload.get("candidates", [])
    if not isinstance(candidates, list):
        raise ValueError("candidates must be a list")
    market = payload.get("market", {}) if isinstance(payload.get("market", {}), dict) else {}
    results = []
    for raw in candidates:
        if not isinstance(raw, dict):
            continue
        candidate = {**raw}
        candidate.setdefault("market_regime", market.get("regime", "unknown"))
        validation = payload.get("strategy_validation", {})
        if isinstance(validation, dict):
            candidate.setdefault("strategy_validation_status", validation.get("status", "experimental"))
        results.append(analyze_candidate(candidate))
    buckets: dict[str, list[dict[str, Any]]] = {name: [] for name in SIGNAL_PRIORITY}
    excluded = []
    for result in results:
        if not result.get("eligible_for_signals"):
            excluded.append(result)
        elif result.get("primary_signal"):
            buckets[result["primary_signal"]].append(result)
    for rows in buckets.values():
        rows.sort(key=lambda row: (row["research_tier"] != "priority", -row["signal_score"], str(row.get("code"))))
        del rows[top:]
    return {
        "schema_version": "2.1.0",
        "objective": "short-term signal discovery, not return probability",
        "cutoff_time": payload.get("cutoff_time"),
        "market": market,
        "buckets": buckets,
        "excluded": excluded,
        "rules": {
            "priority_requires": "quality>=80, evidence>=50, business support, non-hostile market, out-of-sample-validated ruleset, no no-chase flag",
            "limit_up_requires": "observed high plus exact exchange-rule limit-up price",
            "main_force_language": "observable capital-behavior proxy only",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect short-term launch and limit-up structures")
    parser.add_argument("input", type=Path)
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise SystemExit("Expected a JSON object")
    report = analyze(payload, max(1, args.top))
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
