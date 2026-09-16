# Contributing

Use Python 3.11 or later. Install with `python -m pip install -e '.[dev]'`.
Run `python -m pytest`, `ruff check .`, and `ruff format --check .` before a PR.
Keep fixtures entirely synthetic. A metric change must update its definition,
a hand-calculated regression test, and the checked-in example output.
Document limitations; do not present observational differences as causal savings.
