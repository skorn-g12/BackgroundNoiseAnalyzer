"""
Read survey responses (CSV: clip_id, label) and survey_mapping.csv;
output recommended dB ranges or medians per label (very_low, low, medium, high, very_high)
for the voice simulator.
Accepts multiple response CSVs; use --output to write label->median_dB mapping (JSON or CSV).
"""
import argparse
import csv
import json
from pathlib import Path

from config import ROOT_DIR, SURVEY_MAPPING_CSV

LABELS = ["very_low", "low", "medium", "high", "very_high"]


def load_mapping(path: Path) -> dict[str, int]:
    """clip_id -> level_db."""
    out = {}
    with open(path, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            out[row["clip_id"]] = int(row["level_db"])
    return out


def load_responses(path: Path) -> list[tuple[str, str]]:
    """(clip_id, label) list. Expects CSV with columns clip_id and label."""
    out = []
    with open(path, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            cid = row.get("clip_id", "").strip()
            label = row.get("label", "").strip().lower()
            if cid and label:
                out.append((cid, label))
    return out


def median_of_sorted(vals: list[int]) -> float:
    if not vals:
        return float("nan")
    n = len(vals)
    mid = n // 2
    return (vals[mid] + vals[mid - 1]) / 2 if n % 2 == 0 else float(vals[mid])


def main() -> None:
    ap = argparse.ArgumentParser(description="Aggregate survey responses and output dB per label.")
    ap.add_argument(
        "responses",
        nargs="+",
        type=Path,
        help="One or more CSV(s) of survey responses with columns: clip_id, label",
    )
    ap.add_argument(
        "--mapping",
        type=Path,
        default=SURVEY_MAPPING_CSV,
        help="survey_mapping.csv path (default: project survey_mapping.csv)",
    )
    ap.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Write label->median_dB mapping to this file (.json or .csv)",
    )
    args = ap.parse_args()

    if not args.mapping.exists():
        print(f"Mapping not found: {args.mapping}")
        return

    clip_to_db = load_mapping(args.mapping)
    all_responses = []
    for path in args.responses:
        if not path.exists():
            print(f"Skip missing: {path}")
            continue
        all_responses.extend(load_responses(path))

    if not all_responses:
        print("No response rows found.")
        return

    # Collect dB values per label
    by_label: dict[str, list[int]] = {lbl: [] for lbl in LABELS}
    for clip_id, label in all_responses:
        if label not in by_label:
            by_label[label] = []
        if clip_id in clip_to_db:
            by_label[label].append(clip_to_db[clip_id])

    # Summary: count, median, min, max per label
    print("Label       Count   Median(dB)   Min(dB)   Max(dB)")
    print("-" * 50)
    medians = {}
    for lbl in LABELS:
        vals = sorted(by_label[lbl])
        if not vals:
            print(f"{lbl:12}      0       -           -         -")
            medians[lbl] = None
            continue
        n = len(vals)
        med = median_of_sorted(vals)
        medians[lbl] = med
        print(f"{lbl:12}  {n:5}   {med:8.1f}   {min(vals):6}   {max(vals):6}")

    print()
    print("Suggested voice simulator levels (median dB per label):")
    for lbl in LABELS:
        m = medians.get(lbl)
        if m is not None:
            print(f"  {lbl}: {m:.1f} dB")
        else:
            print(f"  {lbl}: (no data)")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        suf = args.output.suffix.lower()
        # Round for output
        mapping_out = {lbl: round(medians[lbl], 1) for lbl in LABELS if medians.get(lbl) is not None}
        if suf == ".json":
            with open(args.output, "w") as f:
                json.dump(mapping_out, f, indent=2)
            print(f"\nWrote mapping to {args.output}")
        elif suf == ".csv":
            with open(args.output, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["label", "median_db"])
                for lbl in LABELS:
                    if medians.get(lbl) is not None:
                        w.writerow([lbl, round(medians[lbl], 1)])
            print(f"\nWrote mapping to {args.output}")
        else:
            print(f"\nUnknown output extension {suf}; use .json or .csv")


if __name__ == "__main__":
    main()
