"""Closed-cohort repair economics; money is stored as integer euro cents."""

from dataclasses import dataclass

import pandas as pd

COSTS = ["parts_cents", "labor_cents", "logistics_cents"]


@dataclass
class Analysis:
    units: pd.DataFrame
    summary: pd.DataFrame
    failures: pd.DataFrame


def validate(cases: pd.DataFrame, events: pd.DataFrame) -> None:
    required_cases = {"case_id", "route", "failure_mode", "outcome"}
    required_events = {"event_id", "case_id", *COSTS}
    for frame, columns, name in [
        (cases, required_cases, "cases"),
        (events, required_events, "events"),
    ]:
        if not columns.issubset(frame.columns):
            raise ValueError(f"{name}: missing columns {sorted(columns - set(frame.columns))}")
        if frame[list(columns)].isna().any().any():
            raise ValueError(f"{name}: null required values")
    if cases.empty:
        raise ValueError("cases: empty cohort")
    for frame, key in [(cases, "case_id"), (events, "event_id")]:
        if frame[key].duplicated().any():
            raise ValueError(f"duplicate {key}")
    for frame, cols in [
        (cases, ["case_id", "route", "failure_mode"]),
        (events, ["case_id", "event_id"]),
    ]:
        for col in cols:
            if not frame[col].map(lambda x: isinstance(x, str) and bool(x.strip())).all():
                raise ValueError(f"{col}: expected nonempty strings")
    if not cases.outcome.isin(["sellable", "scrapped"]).all():
        raise ValueError("outcome: closed cohort must be sellable or scrapped")
    if set(events.case_id) != set(cases.case_id):
        raise ValueError("each case needs events; orphan events are forbidden")
    for col in COSTS:
        if not pd.api.types.is_integer_dtype(events[col]) or pd.api.types.is_bool_dtype(
            events[col]
        ):
            raise ValueError(f"{col}: expected integer cents")
        if (events[col] < 0).any() or (events[col] > 100_000_000).any():
            raise ValueError(f"{col}: expected nonnegative, bounded repair cost")


def summarize(units: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    result = (
        units.groupby(keys, dropna=False)
        .agg(
            cases=("case_id", "size"),
            sellable_units=("sellable", "sum"),
            total_cost_cents=("total_cost_cents", "sum"),
            repeat_repair_units=("repeat_repair", "sum"),
            scrapped_cost_cents=("scrapped_cost_cents", "sum"),
        )
        .reset_index()
    )
    result["yield_rate"] = result.sellable_units / result.cases
    result["cost_per_sellable_eur"] = (result.total_cost_cents / 100).div(
        result.sellable_units.where(result.sellable_units > 0)
    )
    result["cost_per_started_eur"] = result.total_cost_cents / 100 / result.cases
    result["repeat_repair_rate"] = result.repeat_repair_units / result.cases
    return result


def analyze(cases: pd.DataFrame, events: pd.DataFrame) -> Analysis:
    validate(cases, events)
    event_costs = events.assign(total_cost_cents=events[COSTS].sum(axis=1))
    costs = event_costs.groupby("case_id").agg(
        total_cost_cents=("total_cost_cents", "sum"), attempts=("event_id", "size")
    )
    units = cases.merge(costs, on="case_id", validate="one_to_one")
    units["sellable"] = units.outcome.eq("sellable")
    units["repeat_repair"] = units.attempts.gt(1)
    units["scrapped_cost_cents"] = units.total_cost_cents.where(~units.sellable, 0)
    summary = summarize(units, ["route"])
    failures = summarize(units, ["failure_mode"]).sort_values(
        ["scrapped_cost_cents", "failure_mode"], ascending=[False, True]
    )
    failures["scrap_cost_share"] = failures.scrapped_cost_cents / max(
        int(failures.scrapped_cost_cents.sum()), 1
    )
    failures["cumulative_scrap_cost_share"] = failures.scrap_cost_share.cumsum()
    return Analysis(units, summary, failures)


def scale_gate(row: dict, min_cases: int = 50, min_yield: float = 0.90) -> str:
    """Illustrative thresholds, not a statistical assurance of future quality."""
    if row["cases"] < min_cases:
        return "HOLD_INSUFFICIENT_SAMPLE"
    if row["yield_rate"] < min_yield:
        return "NO_GO_QUALITY"
    return "ELIGIBLE_FOR_CONTROLLED_PILOT"
