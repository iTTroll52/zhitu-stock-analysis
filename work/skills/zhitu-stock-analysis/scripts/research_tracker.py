#!/usr/bin/env python3
"""Point-in-time signal ledger and T+1/T+5/T+20 outcome evaluator."""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
import uuid
from pathlib import Path
from typing import Any


HORIZONS = (1, 5, 20)

SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
  id TEXT PRIMARY KEY,
  code TEXT NOT NULL,
  signal_date TEXT NOT NULL,
  cutoff_time TEXT NOT NULL,
  signal_price REAL NOT NULL,
  benchmark TEXT,
  benchmark_price REAL,
  objective TEXT NOT NULL,
  score REAL,
  ruleset_version TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  UNIQUE(code, cutoff_time, objective, ruleset_version)
);
CREATE TABLE IF NOT EXISTS snapshots (
  trade_date TEXT NOT NULL,
  code TEXT NOT NULL,
  close REAL NOT NULL,
  high REAL,
  previous_close REAL,
  limit_up_price REAL,
  benchmark TEXT,
  benchmark_close REAL,
  PRIMARY KEY(trade_date, code)
);
CREATE TABLE IF NOT EXISTS outcomes (
  signal_id TEXT NOT NULL,
  horizon INTEGER NOT NULL,
  target_date TEXT NOT NULL,
  stock_return REAL NOT NULL,
  benchmark_return REAL,
  excess_return REAL,
  hit INTEGER NOT NULL,
  PRIMARY KEY(signal_id, horizon),
  FOREIGN KEY(signal_id) REFERENCES signals(id)
);
"""


def connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    existing = {row[1] for row in connection.execute("PRAGMA table_info(snapshots)")}
    for name, sql_type in (("high", "REAL"), ("previous_close", "REAL"), ("limit_up_price", "REAL")):
        if name not in existing:
            connection.execute(f"ALTER TABLE snapshots ADD COLUMN {name} {sql_type}")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.commit()
    return connection


def _rows(payload: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        payload = payload.get(key, payload)
    if not isinstance(payload, list):
        raise ValueError(f"Expected a list for {key}")
    return [row for row in payload if isinstance(row, dict)]


def record_signals(connection: sqlite3.Connection, rows: list[dict[str, Any]]) -> int:
    inserted = 0
    for row in rows:
        code = str(row["code"])
        cutoff = str(row["cutoff_time"])
        signal_date = str(row.get("signal_date") or cutoff[:10])
        signal_id = str(row.get("id") or uuid.uuid4())
        connection.execute(
            """INSERT OR IGNORE INTO signals
            (id, code, signal_date, cutoff_time, signal_price, benchmark, benchmark_price,
             objective, score, ruleset_version, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                signal_id,
                code,
                signal_date,
                cutoff,
                float(row["signal_price"]),
                row.get("benchmark"),
                float(row["benchmark_price"]) if row.get("benchmark_price") is not None else None,
                str(row["objective"]),
                float(row["score"]) if row.get("score") is not None else None,
                str(row.get("ruleset_version", "2.0.0")),
                json.dumps(row, ensure_ascii=False, sort_keys=True),
            ),
        )
        inserted += connection.execute("SELECT changes()").fetchone()[0]
    connection.commit()
    return inserted


def record_snapshots(connection: sqlite3.Connection, rows: list[dict[str, Any]]) -> int:
    changed = 0
    for row in rows:
        connection.execute(
            """INSERT INTO snapshots(trade_date, code, close, high, previous_close, limit_up_price, benchmark, benchmark_close)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(trade_date, code) DO UPDATE SET
              close=excluded.close, high=excluded.high, previous_close=excluded.previous_close,
              limit_up_price=excluded.limit_up_price, benchmark=excluded.benchmark,
              benchmark_close=excluded.benchmark_close""",
            (
                str(row["trade_date"]),
                str(row["code"]),
                float(row["close"]),
                float(row["high"]) if row.get("high") is not None else None,
                float(row["previous_close"]) if row.get("previous_close") is not None else None,
                float(row["limit_up_price"]) if row.get("limit_up_price") is not None else None,
                row.get("benchmark"),
                float(row["benchmark_close"]) if row.get("benchmark_close") is not None else None,
            ),
        )
        changed += 1
    connection.commit()
    return changed


def _objective_horizons(objective: str) -> tuple[int, ...]:
    normalized = objective.lower().replace(" ", "_")
    if normalized.startswith(("t+1_", "t1_", "next_session_")):
        return (1,)
    if normalized.startswith(("t+5_", "t5_", "five_session_")):
        return (5,)
    if normalized.startswith(("t+20_", "t20_", "twenty_session_")):
        return (20,)
    return HORIZONS


def _is_hit(
    objective: str,
    stock_return: float,
    excess_return: float | None,
    *,
    high: float | None,
    limit_up_price: float | None,
) -> bool | None:
    normalized = objective.lower().replace(" ", "_")
    if "limit_up" in normalized:
        if high is None or limit_up_price is None:
            return None
        return high >= limit_up_price
    if "excess" in normalized:
        return excess_return is not None and excess_return > 0
    return stock_return > 0


def evaluate(connection: sqlite3.Connection) -> int:
    inserted = 0
    signals = connection.execute("SELECT * FROM signals ORDER BY cutoff_time").fetchall()
    for signal in signals:
        snapshots = connection.execute(
            "SELECT * FROM snapshots WHERE code=? AND trade_date>? ORDER BY trade_date",
            (signal["code"], signal["signal_date"]),
        ).fetchall()
        for horizon in _objective_horizons(signal["objective"]):
            if len(snapshots) < horizon:
                continue
            target = snapshots[horizon - 1]
            stock_return = (target["close"] / signal["signal_price"] - 1) * 100
            benchmark_return = None
            if signal["benchmark_price"] and target["benchmark_close"] is not None:
                benchmark_return = (target["benchmark_close"] / signal["benchmark_price"] - 1) * 100
            excess = stock_return - benchmark_return if benchmark_return is not None else None
            hit_value = _is_hit(
                signal["objective"],
                stock_return,
                excess,
                high=target["high"],
                limit_up_price=target["limit_up_price"],
            )
            if hit_value is None:
                continue
            hit = int(hit_value)
            connection.execute(
                """INSERT OR REPLACE INTO outcomes
                (signal_id, horizon, target_date, stock_return, benchmark_return, excess_return, hit)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (signal["id"], horizon, target["trade_date"], stock_return, benchmark_return, excess, hit),
            )
            inserted += 1
    connection.commit()
    return inserted


def wilson_interval(hits: int, total: int, z: float = 1.96) -> tuple[float, float] | None:
    if total == 0:
        return None
    p = hits / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denominator
    return max(0, center - margin), min(1, center + margin)


def report(connection: sqlite3.Connection, min_sample: int = 30) -> dict[str, Any]:
    rows = connection.execute(
        """SELECT s.objective, s.ruleset_version, o.horizon, COUNT(o.hit) AS n, SUM(o.hit) AS hits,
        AVG(o.stock_return) AS avg_stock_return, AVG(o.excess_return) AS avg_excess_return
        FROM outcomes o JOIN signals s ON s.id=o.signal_id
        GROUP BY s.objective, s.ruleset_version, o.horizon
        ORDER BY s.objective, s.ruleset_version, o.horizon"""
    ).fetchall()
    groups = []
    for row in rows:
        interval = wilson_interval(int(row["hits"]), int(row["n"]))
        groups.append(
            {
                "objective": row["objective"],
                "ruleset_version": row["ruleset_version"],
                "horizon": row["horizon"],
                "sample_size": row["n"],
                "hits": row["hits"],
                "hit_rate": row["hits"] / row["n"],
                "wilson_95": list(interval) if interval else None,
                "avg_stock_return_pct": row["avg_stock_return"],
                "avg_excess_return_pct": row["avg_excess_return"],
                "sample_status": "minimum_reached" if row["n"] >= min_sample else "insufficient_sample",
            }
        )
    return {
        "groups": groups,
        "minimum_sample_reference": min_sample,
        "publication_rule": "Keep each objective and ruleset_version separate. Minimum sample size alone does not prove out-of-sample validity.",
        "warning": "Do not convert scores to probabilities until sample size, base rate, costs, fill constraints, and out-of-sample calibration are adequate.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Track and evaluate point-in-time research signals")
    parser.add_argument("--db", type=Path, default=Path("zhitu-research.sqlite3"))
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init")
    record_parser = subparsers.add_parser("record")
    record_parser.add_argument("input", type=Path)
    snapshot_parser = subparsers.add_parser("snapshot")
    snapshot_parser.add_argument("input", type=Path)
    subparsers.add_parser("evaluate")
    report_parser = subparsers.add_parser("report")
    report_parser.add_argument("--min-sample", type=int, default=30)
    args = parser.parse_args()
    connection = connect(args.db)
    if args.command == "init":
        output: Any = {"initialized": str(args.db)}
    elif args.command == "record":
        payload = json.loads(args.input.read_text(encoding="utf-8-sig"))
        output = {"signals_inserted": record_signals(connection, _rows(payload, "signals"))}
    elif args.command == "snapshot":
        payload = json.loads(args.input.read_text(encoding="utf-8-sig"))
        output = {"snapshots_changed": record_snapshots(connection, _rows(payload, "snapshots"))}
    elif args.command == "evaluate":
        output = {"outcomes_written": evaluate(connection)}
    else:
        output = report(connection, max(1, args.min_sample))
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
