"""
Read survey responses (CSV: clip_id, label) and survey_mapping.csv;
compute median dB per label per category (e.g. Cafe's very_low -> X dB, Airport's low -> Y dB).
Output: per-category mappings for the voice simulator.
Accepts multiple response CSVs; use --output to write (JSON or CSV).
"""
import argparse
import csv
import json
from pathlib import Path

from config import CATEGORIES, SURVEY_MAPPING_CSV

LABELS = ["very_low", "low", "medium", "high", "very_high"]


def load_mapping_with_category(path: Path) -> tuple[dict[str, int], dict[str, str]]:
    """Return (clip_id -> level_db, clip_id -> category)."""
    clip_to_db = {}
    clip_to_category = {}
    with open(path, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            cid = row["clip_id"]
            clip_to_db[cid] = int(row["level_db"])
            clip_to_category[cid] = row["category"]
    return clip_to_db, clip_to_category


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
    ap = argparse.ArgumentParser(description="Aggregate survey responses; output median dB per label per category.")
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
        help="Write per-category label->median_dB to this file (.json or .csv)",
    )
    args = ap.parse_args()

    if not args.mapping.exists():
        print(f"Mapping not found: {args.mapping}")
        return

    clip_to_db, clip_to_category = load_mapping_with_category(args.mapping)
    all_responses = []
    for path in args.responses:
        if not path.exists():
            print(f"Skip missing: {path}")
            continue
        all_responses.extend(load_responses(path))

    if not all_responses:
        print("No response rows found.")
        return

    # Per category: label -> list of dB values
    by_category: dict[str, dict[str, list[int]]] = {}
    for cat in CATEGORIES:
        by_category[cat] = {lbl: [] for lbl in LABELS}

    for clip_id, label in all_responses:
        if clip_id not in clip_to_db or clip_id not in clip_to_category:
            continue
        cat = clip_to_category[clip_id]
        db = clip_to_db[clip_id]
        if cat not in by_category:
            by_category[cat] = {lbl: [] for lbl in LABELS}
        if label not in by_category[cat]:
            by_category[cat][label] = []
        by_category[cat][label].append(db)

    # Compute median per category per label; print and build output
    per_category_medians: dict[str, dict[str, float]] = {}
    for cat in CATEGORIES:
        per_category_medians[cat] = {}
        print(f"\n--- {cat} ---")
        print("Label       Count   Median(dB)   Min(dB)   Max(dB)")
        print("-" * 50)
        for lbl in LABELS:
            vals = sorted(by_category[cat].get(lbl, []))
            if not vals:
                print(f"{lbl:12}      0       -           -         -")
                per_category_medians[cat][lbl] = None
                continue
            med = median_of_sorted(vals)
            per_category_medians[cat][lbl] = med
            print(f"{lbl:12}  {len(vals):5}   {med:8.1f}   {min(vals):6}   {max(vals):6}")
        print(f"  -> Voice simulator: very_low={per_category_medians[cat].get('very_low')}, low={per_category_medians[cat].get('low')}, medium={per_category_medians[cat].get('medium')}, high={per_category_medians[cat].get('high')}, very_high={per_category_medians[cat].get('very_high')} dB")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        suf = args.output.suffix.lower()
        # Round for output
        out_data = {}
        for cat in CATEGORIES:
            out_data[cat] = {
                lbl: round(per_category_medians[cat][lbl], 1)
                for lbl in LABELS
                if per_category_medians[cat].get(lbl) is not None
            }
        if suf == ".json":
            with open(args.output, "w") as f:
                json.dump(out_data, f, indent=2)
            print(f"\nWrote per-category mapping to {args.output}")
        elif suf == ".csv":
            with open(args.output, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["category", "label", "median_db"])
                for cat in CATEGORIES:
                    for lbl in LABELS:
                        m = per_category_medians[cat].get(lbl)
                        if m is not None:
                            w.writerow([cat, lbl, round(m, 1)])
            print(f"\nWrote per-category mapping to {args.output}")
        else:
            print(f"\nUnknown output extension {suf}; use .json or .csv")


if __name__ == "__main__":
    main()
