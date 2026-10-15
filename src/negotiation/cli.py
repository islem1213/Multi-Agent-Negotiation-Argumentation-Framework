"""Command-line interface: ``negotiate run <scenario.json>`` and ``negotiate tournament``."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .metrics import evaluate
from .reporting import format_argument_graph, format_metrics, format_table, format_transcript
from .schemas import PriceNegotiationScenario
from .tournament import random_scenarios, run, run_tournament, summarize


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="negotiate", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="run one scenario from a JSON file")
    p_run.add_argument("scenario", type=Path)
    p_run.add_argument("--json", action="store_true", help="print the full trace and metrics as JSON")
    p_run.add_argument("--out", type=Path, help="also save the replayable trace to this JSON file")

    p_tour = sub.add_parser("tournament", help="compare concession tactics on random scenarios")
    p_tour.add_argument("--n", type=int, default=200)
    p_tour.add_argument("--seed", type=int, default=0)
    p_tour.add_argument("--rounds", type=int, default=8)

    args = parser.parse_args(argv)
    if args.command == "run":
        scenario = PriceNegotiationScenario.model_validate_json(args.scenario.read_text(encoding="utf-8"))
        result = run(scenario)
        metrics = evaluate(result, scenario)
        if args.out:
            args.out.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        if args.json:
            print(json.dumps({"result": result.model_dump(mode="json"),
                              "metrics": metrics.model_dump(mode="json")}, indent=2))
        else:
            print(format_transcript(result, scenario), format_argument_graph(result),
                  format_metrics(metrics), sep="\n\n")
    else:
        rows = run_tournament(random_scenarios(args.n, seed=args.seed, max_rounds=args.rounds))
        print(f"{args.n} scenarios x {len(rows) // max(args.n, 1)} tactic pairings (seed={args.seed})\n")
        print(format_table(summarize(rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
