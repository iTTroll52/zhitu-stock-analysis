#!/usr/bin/env python3
"""Safely test core Zhitu API access without printing token-bearing URLs or payloads."""

from __future__ import annotations

import json
import sys

from data_quality import validate_financial_ratios, validate_quote, validate_stock_list
from zhitu_client import ZhituClient, ZhituError


TESTS = (
    ("stock_list", {}, {}, validate_stock_list),
    ("st_list", {}, {}, validate_stock_list),
    ("quote", {"code": "000001"}, {}, validate_quote),
    ("financial_ratios", {"symbol": "000001.SZ"}, {"st": "20250101"}, validate_financial_ratios),
)


def safe_summary(name: str, payload: object) -> dict[str, object]:
    if isinstance(payload, list):
        records = len(payload)
        payload_type = "list"
    elif isinstance(payload, dict):
        data = payload.get("data")
        records = len(data) if isinstance(data, list) else 1
        payload_type = "object"
    else:
        records = 0 if payload is None else 1
        payload_type = type(payload).__name__
    return {"test": name, "ok": True, "type": payload_type, "records": records}


def main() -> int:
    try:
        client = ZhituClient()
    except ZhituError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    failures = 0
    for name, path_values, params, validator in TESTS:
        try:
            result = client.get(name, params=params, force=True, **path_values)
            payload = result.payload
            summary = safe_summary(name, payload)
            quality = validator(payload)
            summary.update(
                {
                    "response_hash": result.response_hash,
                    "quality_score": quality["quality_score"],
                    "quality_status": quality["status"],
                    "quality_issue_codes": [item["code"] for item in quality["issues"]],
                }
            )
            if quality["status"] == "fail":
                failures += 1
                summary["ok"] = False
            print(json.dumps(summary))
        except ZhituError as exc:
            failures += 1
            print(json.dumps({"test": name, "ok": False, "error": str(exc)}))

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
