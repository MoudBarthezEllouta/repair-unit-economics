"""Entirely invented population; route assignment is random within failure family."""

from random import Random

import pandas as pd


def generate(n: int = 1200, seed: int = 17) -> tuple[pd.DataFrame, pd.DataFrame]:
    if n < 1:
        raise ValueError("n must be positive")
    rng = Random(seed)
    cases, events = [], []
    for i in range(n):
        case = f"SIM-{i:06d}"
        failure = rng.choice(["power", "display", "housing"])
        route = rng.choice(["standard", "pilot"])
        # Pilot looks cheaper per start but housing quality is deliberately poor.
        probability = 0.62 if route == "pilot" and failure == "housing" else 0.95
        outcome = "sellable" if rng.random() < probability else "scrapped"
        cases.append(dict(case_id=case, route=route, failure_mode=failure, outcome=outcome))
        attempts = 2 if rng.random() < (0.30 if route == "pilot" else 0.12) else 1
        for attempt in range(attempts):
            events.append(
                dict(
                    event_id=f"{case}-A{attempt + 1}",
                    case_id=case,
                    parts_cents=rng.randint(600, 1600),
                    labor_cents=rng.randint(400, 900)
                    if route == "pilot"
                    else rng.randint(900, 1500),
                    logistics_cents=150,
                )
            )
    return pd.DataFrame(cases), pd.DataFrame(events)
