"""Run the full reconciliation over the real database and print every claim
measurement, plus a sample of disagreement rows per cause.

    python scripts/run_measurements.py > docs/measurement_output.txt
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import duckdb  # noqa: E402

from featurex import load, measurements, reconcile  # noqa: E402


def main() -> None:
    con = duckdb.connect(str(load.DB_PATH), read_only=True)
    reconciled = reconcile.reconcile_all_fields(con)
    reconciled.to_parquet(str(load.DB_PATH.parent / "reconciled.parquet"))

    results = {
        "scale": measurements.measure_scale(con),
        "point_in_time": measurements.measure_point_in_time(con, reconciled),
        "oracle_determinism": measurements.measure_oracle_determinism(con),
        "field_agreement": measurements.measure_field_agreement(reconciled),
        "disagreement_classification": measurements.measure_disagreement_classification(reconciled),
    }

    for name, m in results.items():
        printable = {k: v for k, v in m.items() if k != "by_field"}
        print(f"=== {name} ===")
        print(json.dumps(printable, indent=2, default=str))
        print()

    print("=== per-field agreement ===")
    by_field = reconciled.groupby("field")["agree"].agg(["sum", "count"])
    by_field["rate_pct"] = (by_field["sum"] / by_field["count"] * 100).round(1)
    print(by_field.to_string())
    print()

    print("=== sample disagreements, one per cause ===")
    disagreements = reconciled[~reconciled["agree"]]
    for cause in sorted(disagreements["cause"].dropna().unique()):
        sample = disagreements[disagreements["cause"] == cause].head(2)
        print(f"-- {cause} --")
        print(sample[["adsh", "field", "oracle_tag", "oracle_value", "text_tag", "text_value"]].to_string())
        print()


if __name__ == "__main__":
    main()
