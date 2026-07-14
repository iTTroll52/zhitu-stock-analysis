#!/usr/bin/env python3
"""Deterministic primary-evidence coverage scoring and research-score caps."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


WEIGHTS = {
    "filing": 20,
    "financial_report": 20,
    "official_company": 10,
    "investor_relations": 10,
    "industry_position": 10,
    "revenue_exposure": 10,
    "order": 10,
    "capacity": 10,
}

PRIMARY_HOST_SUFFIXES = (
    "cninfo.com.cn",
    "sse.com.cn",
    "szse.cn",
    "gov.cn",
    "csrc.gov.cn",
    "pbc.gov.cn",
    "ndrc.gov.cn",
    "miit.gov.cn",
    "mofcom.gov.cn",
)

STRENGTH_FACTOR = {"primary": 1.0, "official_company": 0.9, "secondary": 0.4, "unverified": 0.0}
STATUS_FACTOR = {"confirmed": 1.0, "partial": 0.5, "contradicted": 0.0, "pending": 0.0}


def _date(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _is_known_primary(url: str) -> bool:
    host = _host(url)
    return any(host == suffix or host.endswith(f".{suffix}") for suffix in PRIMARY_HOST_SUFFIXES)


def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    cutoff = _date(payload.get("cutoff_time"))
    items = payload.get("evidence", [])
    if not isinstance(items, list):
        raise ValueError("evidence must be a list")
    best: dict[str, float] = {category: 0.0 for category in WEIGHTS}
    flags: list[dict[str, str]] = []
    accepted: list[dict[str, Any]] = []

    for index, raw in enumerate(items):
        if not isinstance(raw, dict):
            flags.append({"code": "row.invalid", "detail": f"Evidence row {index} is not an object"})
            continue
        category = str(raw.get("category", ""))
        if category not in WEIGHTS:
            flags.append({"code": "category.invalid", "detail": f"Unknown category at row {index}"})
            continue
        url = str(raw.get("source_url", ""))
        available_at = _date(raw.get("available_at") or raw.get("published_at"))
        if not url.startswith(("https://", "http://")):
            flags.append({"code": "source.invalid", "detail": f"Missing valid source URL at row {index}"})
            continue
        if cutoff and (available_at is None or available_at > cutoff):
            flags.append({"code": "point_in_time.rejected", "detail": f"Evidence unavailable by cutoff at row {index}"})
            continue

        strength = str(raw.get("strength", "unverified"))
        status = str(raw.get("status", "pending"))
        if strength == "primary" and category != "official_company" and not _is_known_primary(url):
            flags.append({"code": "primary_host.unverified", "detail": f"Primary label requires manual host verification at row {index}"})
            strength = "secondary"
        factor = STRENGTH_FACTOR.get(strength, 0.0) * STATUS_FACTOR.get(status, 0.0)
        best[category] = max(best[category], WEIGHTS[category] * factor)
        accepted.append({"category": category, "source_url": url, "strength": strength, "status": status, "available_at": raw.get("available_at") or raw.get("published_at")})

    coverage_score = round(sum(best.values()), 2)
    present = {category for category, score in best.items() if score > 0}
    score_cap = 100
    cap_reasons: list[str] = []
    if not present.intersection({"filing", "financial_report", "official_company", "investor_relations"}):
        score_cap = min(score_cap, 45)
        cap_reasons.append("No effective filing, financial report, official-company, or IR evidence")
    if "financial_report" not in present:
        score_cap = min(score_cap, 50)
        cap_reasons.append("No usable financial report")
    if payload.get("catalyst_core") and not present.intersection({"filing", "financial_report", "official_company", "investor_relations", "revenue_exposure"}):
        score_cap = min(score_cap, 60)
        cap_reasons.append("Core catalyst lacks primary company evidence")
    if payload.get("order_core") and "order" not in present:
        cap_reasons.append("Core order thesis is unverified; high-priority tier prohibited")
    if payload.get("capacity_core") and "capacity" not in present:
        cap_reasons.append("Core capacity thesis is unverified; high-priority tier prohibited")

    proposed = payload.get("proposed_research_score")
    adjusted = min(float(proposed), score_cap) if proposed is not None else None
    high_priority_allowed = adjusted is not None and adjusted >= 75 and not any("prohibited" in reason for reason in cap_reasons)
    return {
        "schema_version": "2.0.0",
        "code": payload.get("code"),
        "cutoff_time": payload.get("cutoff_time"),
        "coverage_score": coverage_score,
        "category_scores": best,
        "score_cap": score_cap,
        "proposed_research_score": proposed,
        "adjusted_research_score": adjusted,
        "high_priority_allowed": high_priority_allowed,
        "cap_reasons": cap_reasons,
        "flags": flags,
        "accepted_evidence": accepted,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply primary-evidence coverage gates")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise SystemExit("Expected a JSON object")
    report = evaluate(payload)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
