#!/usr/bin/env python3
"""Safely test core Zhitu API access without printing the token or response data."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


BASE_URL = "https://api.zhituapi.com"
TESTS = (
    ("stock_list", "/hs/list/all", {}),
    ("st_list", "/hs/list/fx", {}),
    ("realtime_main_board", "/hs/real/ssjy/000001", {}),
    ("financial_ratios", "/hs/fin/ratios/000001.SZ", {"st": "20250101"}),
)


def request_json(path: str, params: dict[str, str], token: str) -> object:
    query = urllib.parse.urlencode({**params, "token": token})
    request = urllib.request.Request(
        f"{BASE_URL}{path}?{query}",
        headers={"User-Agent": "zhitu-stock-analysis/1.0"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read())


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


def load_token() -> str:
    token = os.environ.get("ZHITU_API_TOKEN", "").strip()
    if token:
        return token

    for filename in (".env.local", ".env"):
        path = Path.cwd() / filename
        if not path.is_file():
            continue
        for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == "ZHITU_API_TOKEN":
                return value.strip().strip('"').strip("'")
    return ""


def main() -> int:
    token = load_token()
    if not token:
        print("ZHITU_API_TOKEN is not configured.", file=sys.stderr)
        return 2

    failures = 0
    for name, path, params in TESTS:
        try:
            print(json.dumps(safe_summary(name, request_json(path, params, token))))
        except urllib.error.HTTPError as exc:
            failures += 1
            print(json.dumps({"test": name, "ok": False, "error": f"HTTP {exc.code}"}))
        except Exception as exc:  # Do not print exception text because it may contain the URL.
            failures += 1
            print(json.dumps({"test": name, "ok": False, "error": type(exc).__name__}))

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
