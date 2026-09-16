import argparse
import json
from pathlib import Path

from .core import analyze, scale_gate
from .demo import generate


def main():
    parser = argparse.ArgumentParser(description="Run synthetic closed-cohort repair analysis")
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    parser.add_argument("--cases", type=int, default=1200)
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()
    cases, events = generate(args.cases, args.seed)
    result = analyze(cases, events)
    result.summary["decision"] = [scale_gate(row) for row in result.summary.to_dict("records")]
    args.output.mkdir(parents=True, exist_ok=True)
    for name, frame in {
        "synthetic_cases": cases,
        "synthetic_events": events,
        "unit_costs": result.units,
        "route_summary": result.summary,
        "failure_pareto": result.failures,
    }.items():
        frame.to_csv(args.output / f"{name}.csv", index=False)
    report = {
        "data": "fully synthetic",
        "seed": args.seed,
        "cases": len(cases),
        "events": len(events),
        "routes": json.loads(result.summary.to_json(orient="records")),
    }
    (args.output / "summary.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(result.summary.to_string(index=False))


if __name__ == "__main__":
    main()
