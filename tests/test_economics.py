import pandas as pd
import pytest

from repair_economics.core import analyze, scale_gate
from repair_economics.demo import generate


def fixture():
    cases = pd.DataFrame(
        [["A", "pilot", "display", "sellable"], ["B", "pilot", "power", "scrapped"]],
        columns=["case_id", "route", "failure_mode", "outcome"],
    )
    events = pd.DataFrame(
        [["1", "A", 1000, 0, 0], ["2", "A", 500, 0, 0], ["3", "B", 2000, 0, 0]],
        columns=["event_id", "case_id", "parts_cents", "labor_cents", "logistics_cents"],
    )
    return cases, events


def test_rework_and_scrap_costs_remain_in_numerator():
    result = analyze(*fixture())
    row = result.summary.iloc[0]
    assert row.total_cost_cents == 3500
    assert row.sellable_units == 1
    assert row.cost_per_sellable_eur == 35
    assert row.cost_per_started_eur == 17.5
    assert row.repeat_repair_rate == 0.5
    assert result.failures.iloc[0].failure_mode == "power"
    assert result.failures.scrapped_cost_cents.sum() == 2000


def test_no_sellable_is_undefined_not_zero():
    cases, events = fixture()
    cases["outcome"] = "scrapped"
    assert pd.isna(analyze(cases, events).summary.iloc[0].cost_per_sellable_eur)


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate_case",
        "duplicate_event",
        "orphan",
        "missing",
        "negative",
        "fractional",
        "null",
        "open",
    ],
)
def test_invalid_inputs_fail(mutation):
    cases, events = fixture()
    if mutation == "duplicate_case":
        cases = pd.concat([cases, cases.iloc[[0]]])
    if mutation == "duplicate_event":
        events = pd.concat([events, events.iloc[[0]]])
    if mutation == "orphan":
        events.loc[0, "case_id"] = "UNKNOWN"
    if mutation == "missing":
        events = events[events.case_id != "B"]
    if mutation == "negative":
        events.loc[0, "parts_cents"] = -1
    if mutation == "fractional":
        events["parts_cents"] = events.parts_cents / 3
    if mutation == "null":
        cases.loc[0, "route"] = None
    if mutation == "open":
        cases.loc[0, "outcome"] = "in_progress"
    with pytest.raises(ValueError):
        analyze(cases, events)


def test_cost_reconciles_and_shuffle_does_not_change_summary():
    cases, events = generate()
    result = analyze(cases, events)
    assert (
        result.units.total_cost_cents.sum()
        == events[["parts_cents", "labor_cents", "logistics_cents"]].sum().sum()
    )
    pd.testing.assert_frame_equal(
        result.summary, analyze(cases.sample(frac=1), events.sample(frac=1)).summary
    )


def test_quality_gate_overrides_low_cost():
    assert scale_gate({"cases": 100, "yield_rate": 0.8}) == "NO_GO_QUALITY"
    assert scale_gate({"cases": 20, "yield_rate": 1.0}) == "HOLD_INSUFFICIENT_SAMPLE"
    assert scale_gate({"cases": 100, "yield_rate": 0.95}) == "ELIGIBLE_FOR_CONTROLLED_PILOT"
