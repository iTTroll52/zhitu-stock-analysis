#!/usr/bin/env python3
"""Verify that a deployed skill contains the complete executable surface."""

from __future__ import annotations

import json
from pathlib import Path

from zhitu_client import CLIENT_VERSION, load_token


REQUIRED = (
    "SKILL.md",
    "agents/openai.yaml",
    "references/analysis-framework.md",
    "references/attention-and-event-reaction.md",
    "references/automation.md",
    "references/data-quality-gates.md",
    "references/global-risk-overlay.md",
    "references/html-report.md",
    "references/launch-and-limit-signals.md",
    "references/market-regime-and-cash.md",
    "references/rotation-candidates-and-positioning.md",
    "references/rule-validation-and-shadow.md",
    "references/sector-rotation.md",
    "references/short-term-selection.md",
    "references/zhitu-api.md",
    "scripts/data_quality.py",
    "scripts/evidence_gate.py",
    "scripts/generate_html_report.py",
    "scripts/market_regime.py",
    "scripts/research_tracker.py",
    "scripts/screen_main_board.py",
    "scripts/short_term_signals.py",
    "scripts/sector_rotation.py",
    "scripts/test_connection.py",
    "scripts/zhitu_client.py",
)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    missing = [path for path in REQUIRED if not (root / path).is_file()]
    report = {
        "skill_root": str(root),
        "client_version": CLIENT_VERSION,
        "complete": not missing,
        "missing": missing,
        "token_configured": bool(load_token()),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
