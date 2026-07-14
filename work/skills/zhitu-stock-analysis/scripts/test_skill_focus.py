#!/usr/bin/env python3

from __future__ import annotations

import unittest
from pathlib import Path


class SkillFocusTests(unittest.TestCase):
    def test_skill_is_short_term_first(self) -> None:
        root = Path(__file__).resolve().parent.parent
        skill = (root / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("short-term trading research", skill)
        self.assertIn("Do not produce long-term picks", skill)
        self.assertNotIn("long-horizon fundamental work", skill)
        self.assertNotIn("swing, or fundamental research", skill)
        self.assertTrue((root / "references" / "short-term-selection.md").is_file())


if __name__ == "__main__":
    unittest.main()
