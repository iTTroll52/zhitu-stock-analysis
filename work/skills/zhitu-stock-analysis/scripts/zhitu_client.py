#!/usr/bin/env python3
"""Safe, rate-limited Zhitu API client with immutable raw-response caching."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_URL = "https://api.zhituapi.com"
CLIENT_VERSION = "2.0.0"
DEFAULT_TIMEOUT = 20.0

ENDPOINTS: dict[str, tuple[str, int]] = {
    "stock_list": ("/hs/list/all", 86_400),
    "st_list": ("/hs/list/fx", 86_400),
    "instrument": ("/hs/instrument/{code}", 86_400),
    "quote": ("/hs/real/ssjy/{code}", 55),
    "multi_quote": ("/hs/public/ssjymore", 55),
    "all_market": ("/hs/public/realall", 60),
    "limit_up": ("/hs/pool/ztgc/{date}", 540),
    "limit_down": ("/hs/pool/dtgc/{date}", 540),
    "broken_limit": ("/hs/pool/zbgc/{date}", 540),
    "latest_bars": ("/hs/latest/{code}/{freq}/{adjust}", 55),
    "history_bars": ("/hs/history/{code}/{freq}/{adjust}", 86_400),
    "daily_indicators": ("/hs/indicators/{code}", 3_600),
    "financial_ratios": ("/hs/fin/ratios/{symbol}", 86_400),
    "capital": ("/hs/fin/capital/{symbol}", 86_400),
    "top_holders": ("/hs/fin/topholder/{symbol}", 86_400),
    "flow_holders": ("/hs/fin/flowholder/{symbol}", 86_400),
    "holder_count": ("/hs/fin/hm/{symbol}", 86_400),
}


class ZhituError(RuntimeError):
    """Base exception that never embeds a token-bearing URL."""


class AuthenticationError(ZhituError):
    pass


class QuotaError(ZhituError):
    pass


class RateLimitError(ZhituError):
    pass


class ResourceError(ZhituError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def load_token() -> str:
    """Load the token without ever returning its location in diagnostics."""
    token = os.environ.get("ZHITU_API_TOKEN", "").strip()
    if token:
        return token

    candidates = [
        Path.home() / ".config" / "zhitu-stock-analysis" / ".env",
        Path.cwd() / ".env.local",
        Path.cwd() / ".env",
    ]
    for path in candidates:
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


def default_cache_dir() -> Path:
    configured = os.environ.get("ZHITU_CACHE_DIR", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".cache" / "zhitu-stock-analysis"


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass(frozen=True)
class ApiResult:
    endpoint: str
    payload: Any
    fetched_at: str
    response_hash: str
    from_cache: bool

    def lineage(self) -> dict[str, Any]:
        return {
            "provider": "zhitu",
            "endpoint": self.endpoint,
            "fetched_at": self.fetched_at,
            "response_hash": self.response_hash,
            "from_cache": self.from_cache,
            "client_version": CLIENT_VERSION,
        }


class CacheStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.raw = root / "raw"
        self.index = root / "index"

    def _key_path(self, key: str) -> Path:
        return self.index / f"{hashlib.sha256(key.encode('utf-8')).hexdigest()}.json"

    def get(self, key: str) -> ApiResult | None:
        index_path = self._key_path(key)
        if not index_path.is_file():
            return None
        try:
            metadata = json.loads(index_path.read_text(encoding="utf-8"))
            if float(metadata["expires_at_epoch"]) < time.time():
                return None
            raw_path = self.root / metadata["raw_path"]
            payload = json.loads(raw_path.read_text(encoding="utf-8"))
            return ApiResult(
                endpoint=metadata["endpoint"],
                payload=payload,
                fetched_at=metadata["fetched_at"],
                response_hash=metadata["response_hash"],
                from_cache=True,
            )
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def put(self, key: str, endpoint: str, payload: Any, ttl_seconds: int) -> ApiResult:
        encoded = _canonical_json(payload)
        response_hash = hashlib.sha256(encoded).hexdigest()
        now = utc_now()
        relative_raw = Path("raw") / now.strftime("%Y/%m/%d") / f"{response_hash}.json"
        raw_path = self.root / relative_raw
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        if not raw_path.exists():
            raw_path.write_bytes(encoded)

        metadata = {
            "endpoint": endpoint,
            "fetched_at": now.isoformat(),
            "expires_at_epoch": time.time() + max(0, ttl_seconds),
            "response_hash": response_hash,
            "raw_path": relative_raw.as_posix(),
            "client_version": CLIENT_VERSION,
        }
        index_path = self._key_path(key)
        index_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = index_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(index_path)
        return ApiResult(endpoint, payload, metadata["fetched_at"], response_hash, False)


class MinuteLimiter:
    """Simple per-process rolling-window limiter."""

    def __init__(self, requests_per_minute: int) -> None:
        if requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be positive")
        self.limit = requests_per_minute
        self.timestamps: list[float] = []

    def acquire(self) -> None:
        now = time.monotonic()
        self.timestamps = [item for item in self.timestamps if now - item < 60]
        if len(self.timestamps) >= self.limit:
            delay = 60 - (now - self.timestamps[0])
            if delay > 0:
                time.sleep(delay)
            now = time.monotonic()
            self.timestamps = [item for item in self.timestamps if now - item < 60]
        self.timestamps.append(time.monotonic())


class ZhituClient:
    def __init__(
        self,
        token: str | None = None,
        *,
        cache_dir: Path | None = None,
        requests_per_minute: int | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = 2,
    ) -> None:
        self.token = (token or load_token()).strip()
        if not self.token:
            raise AuthenticationError("ZHITU_API_TOKEN is not configured")
        configured_rate = int(os.environ.get("ZHITU_REQUESTS_PER_MINUTE", "1000"))
        self.limiter = MinuteLimiter(requests_per_minute or configured_rate)
        self.cache = CacheStore(cache_dir or default_cache_dir())
        self.timeout = timeout
        self.retries = max(0, retries)

    @staticmethod
    def render_path(endpoint: str, **path_values: str) -> tuple[str, int]:
        if endpoint not in ENDPOINTS:
            raise ResourceError(f"Unknown endpoint name: {endpoint}")
        template, ttl = ENDPOINTS[endpoint]
        try:
            path = template.format(**path_values)
        except KeyError as exc:
            raise ResourceError(f"Missing path parameter: {exc.args[0]}") from None
        return path, ttl

    def get(
        self,
        endpoint: str,
        *,
        params: dict[str, str] | None = None,
        force: bool = False,
        ttl_seconds: int | None = None,
        **path_values: str,
    ) -> ApiResult:
        path, default_ttl = self.render_path(endpoint, **path_values)
        clean_params = {str(key): str(value) for key, value in (params or {}).items() if value is not None}
        cache_key = json.dumps([endpoint, path, sorted(clean_params.items())], separators=(",", ":"))
        if not force:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        payload = self._request(path, clean_params, endpoint)
        return self.cache.put(cache_key, endpoint, payload, default_ttl if ttl_seconds is None else ttl_seconds)

    def _request(self, path: str, params: dict[str, str], endpoint: str) -> Any:
        query = urllib.parse.urlencode({**params, "token": self.token})
        request = urllib.request.Request(
            f"{BASE_URL}{path}?{query}",
            headers={"User-Agent": f"zhitu-stock-analysis/{CLIENT_VERSION}"},
        )
        for attempt in range(self.retries + 1):
            self.limiter.acquire()
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read())
            except urllib.error.HTTPError as exc:
                if exc.code == 401:
                    raise QuotaError(f"Daily quota exhausted for endpoint {endpoint}") from None
                if exc.code == 402:
                    raise AuthenticationError("Invalid Zhitu token") from None
                if exc.code == 404:
                    raise ResourceError(f"Resource not found for endpoint {endpoint}") from None
                retryable = exc.code == 429 or 500 <= exc.code < 600
                if not retryable or attempt >= self.retries:
                    if exc.code == 429:
                        raise RateLimitError(f"Rate limited on endpoint {endpoint}") from None
                    raise ZhituError(f"HTTP {exc.code} from endpoint {endpoint}") from None
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                if attempt >= self.retries:
                    raise ZhituError(f"{type(exc).__name__} from endpoint {endpoint}") from None
            time.sleep(min(8.0, (2**attempt) + random.random()))
        raise ZhituError(f"Request failed for endpoint {endpoint}")


def _parse_key_values(values: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"Expected key=value: {item}")
        key, value = item.split("=", 1)
        parsed[key] = value
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe Zhitu API client")
    parser.add_argument("endpoint", choices=sorted(ENDPOINTS))
    parser.add_argument("--path", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--param", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--output", type=Path, help="Write payload and lineage JSON to a file")
    args = parser.parse_args()
    try:
        result = ZhituClient().get(
            args.endpoint,
            params=_parse_key_values(args.param),
            force=args.force,
            **_parse_key_values(args.path),
        )
    except (ZhituError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    output = {"lineage": result.lineage(), "payload": result.payload}
    rendered = json.dumps(output, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
        print(json.dumps(result.lineage(), ensure_ascii=False))
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
