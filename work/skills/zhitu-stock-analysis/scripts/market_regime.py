#!/usr/bin/env python3
"""Classify A-share market regime and participate/wait/cash posture.

The output is a deterministic research state, not a return forecast or
personalized allocation instruction. Inputs must be point-in-time aggregates.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def ratio(value: Any) -> float | None:
    result = number(value)
    if result is None:
        return None
    return result / 100 if result > 1 else result


def _quality_score(payload: dict[str, Any]) -> float | None:
    quality = payload.get("data_quality")
    if isinstance(quality, dict):
        return number(quality.get("score"))
    return number(payload.get("quality_score"))


def _component(values: list[float | None]) -> float | None:
    clean = [value for value in values if value is not None]
    return sum(clean) / len(clean) if clean else None


def analyze(payload: dict[str, Any]) -> dict[str, Any]:
    quality = _quality_score(payload)
    cutoff = payload.get("cutoff_time") or payload.get("data_cutoff")
    source_time = payload.get("source_time")
    flags: list[str] = []
    if quality is None or quality < 80:
        flags.append("data quality below 80 or missing")
    if not cutoff:
        flags.append("prediction cutoff missing")
    if not source_time:
        flags.append("market source_time missing")

    indices = payload.get("indices", [])
    if not isinstance(indices, list):
        indices = []
    index_changes = [
        value
        for row in indices
        if isinstance(row, dict) and (value := number(row.get("change_pct"))) is not None
    ]
    index_average = sum(index_changes) / len(index_changes) if index_changes else None
    positive_index_ratio = (
        sum(value > 0 for value in index_changes) / len(index_changes) if index_changes else None
    )

    breadth = payload.get("breadth", {}) if isinstance(payload.get("breadth"), dict) else {}
    advancers = number(breadth.get("advancers"))
    decliners = number(breadth.get("decliners"))
    advancer_ratio = None
    if advancers is not None and decliners is not None and advancers + decliners > 0:
        advancer_ratio = advancers / (advancers + decliners)
    above_ma20 = ratio(breadth.get("above_ma20_pct"))

    liquidity = payload.get("liquidity", {}) if isinstance(payload.get("liquidity"), dict) else {}
    amount_ratio = number(liquidity.get("same_time_amount_ratio"))

    limits = payload.get("limits", {}) if isinstance(payload.get("limits"), dict) else {}
    limit_up = number(limits.get("limit_up")) or 0
    limit_down = number(limits.get("limit_down")) or 0
    broken = number(limits.get("broken")) or 0
    limit_balance = (limit_up - limit_down) / (limit_up + limit_down) if limit_up + limit_down > 0 else None
    broken_rate = broken / (limit_up + broken) if limit_up + broken > 0 else None

    sectors = payload.get("sectors", {}) if isinstance(payload.get("sectors"), dict) else {}
    strengthening = number(sectors.get("strengthening")) or 0
    accelerating = number(sectors.get("accelerating")) or 0
    diverging = number(sectors.get("diverging")) or 0
    fading = number(sectors.get("fading")) or 0
    sector_total = strengthening + accelerating + diverging + fading
    sector_confirmation = (strengthening + accelerating) / sector_total if sector_total else None
    sector_risk = (diverging + fading) / sector_total if sector_total else None

    components = {
        "index_trend": _component([
            clamp(50 + index_average * 12) if index_average is not None else None,
            positive_index_ratio * 100 if positive_index_ratio is not None else None,
        ]),
        "breadth": _component([
            advancer_ratio * 100 if advancer_ratio is not None else None,
            above_ma20 * 100 if above_ma20 is not None else None,
        ]),
        "liquidity": clamp((amount_ratio - 0.7) / 0.6 * 100) if amount_ratio is not None else None,
        "limit_structure": _component([
            (limit_balance + 1) * 50 if limit_balance is not None else None,
            (1 - broken_rate) * 100 if broken_rate is not None else None,
        ]),
        "sector_confirmation": _component([
            sector_confirmation * 100 if sector_confirmation is not None else None,
            (1 - sector_risk) * 100 if sector_risk is not None else None,
        ]),
    }
    available_components = [value for value in components.values() if value is not None]
    if len(available_components) < 4:
        flags.append("fewer than four independent market component groups")
    risk_on_score = sum(available_components) / len(available_components) if available_components else None

    crisis = bool(
        advancer_ratio is not None
        and advancer_ratio < 0.25
        and limit_down >= max(20, limit_up * 0.8)
    )
    if risk_on_score is None:
        regime = "unknown"
    elif crisis:
        regime = "crisis"
    elif risk_on_score >= 70 and (advancer_ratio or 0) >= 0.60 and (above_ma20 or 0) >= 0.55:
        regime = "broad_bull"
    elif risk_on_score >= 58:
        regime = "structural_bull"
    elif risk_on_score <= 30 and (advancer_ratio or 1) <= 0.35 and (above_ma20 or 1) <= 0.40:
        regime = "broad_bear"
    elif risk_on_score <= 42:
        regime = "structural_bear"
    elif 45 <= risk_on_score <= 58:
        regime = "range"
    else:
        regime = "transition"

    posture_map = {
        "broad_bull": ("participate", "40%-60%"),
        "structural_bull": ("selective_participation", "25%-45%"),
        "range": ("wait_or_selective", "10%-30%"),
        "transition": ("wait", "0%-20%"),
        "structural_bear": ("cash_preferred", "0%-15%"),
        "broad_bear": ("cash", "0%-5%"),
        "crisis": ("cash", "0%-5%"),
        "unknown": ("insufficient_data", None),
    }
    posture, research_band = posture_map[regime]

    validation = payload.get("strategy_validation", {})
    if not isinstance(validation, dict):
        validation = {}
    validation_status = str(validation.get("status", "unvalidated"))
    validated = validation_status in {"validated", "out_of_sample_validated"}
    decision_allowed = not flags and risk_on_score is not None
    publication_status = "validated_research_state" if decision_allowed and validated else "experimental_research_state"
    if not decision_allowed:
        posture, research_band, publication_status = "insufficient_data", None, "blocked"

    reasons: list[str] = []
    counter_evidence: list[str] = []
    if advancer_ratio is not None:
        (reasons if advancer_ratio >= 0.55 else counter_evidence).append(
            f"advancer_ratio={advancer_ratio:.3f}"
        )
    if amount_ratio is not None:
        (reasons if amount_ratio >= 1 else counter_evidence).append(
            f"same_time_amount_ratio={amount_ratio:.3f}"
        )
    if sector_confirmation is not None:
        (reasons if sector_confirmation >= 0.5 else counter_evidence).append(
            f"sector_confirmation={sector_confirmation:.3f}"
        )
    if broken_rate is not None:
        (reasons if broken_rate <= 0.25 else counter_evidence).append(
            f"broken_rate={broken_rate:.3f}"
        )

    return {
        "schema_version": "1.0.0",
        "cutoff_time": cutoff,
        "source_time": source_time,
        "quality_score": quality,
        "decision_allowed": decision_allowed,
        "publication_status": publication_status,
        "strategy_validation_status": validation_status,
        "regime": regime,
        "posture": posture,
        "research_exposure_band": research_band,
        "risk_on_score": round(risk_on_score, 2) if risk_on_score is not None else None,
        "components": {key: round(value, 2) if value is not None else None for key, value in components.items()},
        "observations": {
            "index_average_change_pct": index_average,
            "positive_index_ratio": positive_index_ratio,
            "advancer_ratio": advancer_ratio,
            "above_ma20_ratio": above_ma20,
            "same_time_amount_ratio": amount_ratio,
            "limit_balance": limit_balance,
            "broken_rate": broken_rate,
            "sector_confirmation": sector_confirmation,
            "sector_risk": sector_risk,
        },
        "reasons": reasons,
        "counter_evidence": counter_evidence,
        "flags": flags,
        "warning": "This is a deterministic research posture, not a return forecast or personalized allocation instruction.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify market regime and cash posture")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise SystemExit("Expected a JSON object")
    rendered = json.dumps(analyze(payload), ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
