#!/usr/bin/env python3
"""activation-evals: score skill trigger evals (ecosystem 15.1 protocol). Skeleton for M1.

This tool never calls a model. A runner (harness-specific, delivered with the M2 eval tooling)
executes each query of `evals/triggers.json` three times on a clean context and writes a results
file:

  {"skill": "write-adr", "results": [{"query": "...", "should_trigger": true, "split": "validation",
                                      "runs": [true, true, false]}]}

  score    precision and recall on the validation split; a query triggers when >= 50% of runs did
  compare  gate a skill change: fails when validation accuracy drops by more than 10 points

  python3 tools/activation_evals.py score results.json
  python3 tools/activation_evals.py compare baseline.json candidate.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys


def triggered(runs: list[bool]) -> bool:
    return bool(runs) and sum(bool(r) for r in runs) / len(runs) >= 0.5


def score(results: list[dict], split: str = "validation") -> dict:
    rows = [r for r in results if r.get("split") == split]
    tp = sum(1 for r in rows if r["should_trigger"] and triggered(r["runs"]))
    fp = sum(1 for r in rows if not r["should_trigger"] and triggered(r["runs"]))
    fn = sum(1 for r in rows if r["should_trigger"] and not triggered(r["runs"]))
    tn = sum(1 for r in rows if not r["should_trigger"] and not triggered(r["runs"]))
    total = len(rows)
    return {
        "split": split,
        "queries": total,
        "precision": tp / (tp + fp) if tp + fp else 1.0,
        "recall": tp / (tp + fn) if tp + fn else 1.0,
        "accuracy": (tp + tn) / total if total else 0.0,
    }


def load(path: pathlib.Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    results = data["results"]
    for r in results:
        if not isinstance(r.get("runs"), list) or "should_trigger" not in r:
            raise ValueError(f"invalid result row: {r}")
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score skill activation evals (no model calls).")
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("score")
    s.add_argument("results", type=pathlib.Path)
    c = sub.add_parser("compare")
    c.add_argument("baseline", type=pathlib.Path)
    c.add_argument("candidate", type=pathlib.Path)
    c.add_argument("--max-drop-points", type=float, default=10.0)
    args = parser.parse_args(argv)
    try:
        if args.command == "score":
            print(json.dumps(score(load(args.results)), indent=2))
            return 0
        base, cand = score(load(args.baseline)), score(load(args.candidate))
    except (OSError, ValueError, KeyError) as exc:
        print(f"::error title=activation-evals::{exc}")
        return 2
    drop = (base["accuracy"] - cand["accuracy"]) * 100
    print(json.dumps({"baseline": base, "candidate": cand, "drop_points": round(drop, 1)}, indent=2))
    if drop > args.max_drop_points:
        print(f"::error title=activation-evals::validation accuracy dropped {drop:.1f} points (max {args.max_drop_points})")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
