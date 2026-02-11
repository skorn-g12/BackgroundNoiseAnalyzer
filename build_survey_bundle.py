"""
Copy selected level-normalized clips into levels/ with anonymized names
(clip_0001.wav, clip_0002.wav, ...) and write survey_mapping.csv
(clip_id, category, sample_id, level_db). Keep survey_mapping.csv private.
"""
import csv
import re
import shutil
from pathlib import Path

from config import ROOT_DIR, CATEGORIES, LEVELS_DIR, SURVEY_MAPPING_CSV

# Pattern for level files: office_01_level_-40db.wav
LEVEL_FILE_PATTERN = re.compile(r"^(.+)_(\d+)_level_(-?\d+)db\.wav$", re.IGNORECASE)


def category_key(name: str) -> str:
    return name[0].lower() + name[1:] if name else name


def collect_level_files() -> list[tuple[Path, str, str, int]]:
    """Collect (path, category, sample_id, level_db) for each level file in category dirs."""
    out = []
    for category in CATEGORIES:
        cat_dir = ROOT_DIR / category
        if not cat_dir.exists():
            continue
        ckey = category_key(category)
        prefix = f"{ckey}_"
        for path in sorted(cat_dir.glob("*_level_*db.wav")):
            stem = path.stem
            m = LEVEL_FILE_PATTERN.match(stem)
            if m:
                cat_prefix, sample_id, level_str = m.group(1), m.group(2), m.group(3)
                if cat_prefix.lower() == ckey.lower():
                    out.append((path, category, f"{int(sample_id):02d}", int(level_str)))
            elif stem.startswith(prefix) and "_level_" in stem:
                # Fallback: parse "office_01_level_-40db"
                rest = stem[len(prefix):]
                if "_level_" in rest:
                    sample_id_part, level_part = rest.split("_level_", 1)
                    if level_part.endswith("db"):
                        level_db = int(level_part[:-2])
                        sample_id = f"{int(sample_id_part):02d}" if sample_id_part.isdigit() else sample_id_part
                        out.append((path, category, sample_id, level_db))
    return sorted(out, key=lambda x: (x[1], x[2], x[3]))


def main() -> None:
    level_files = collect_level_files()
    if not level_files:
        print("No level-normalized files found. Run generate_levels.py first.")
        return

    LEVELS_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for idx, (path, category, sample_id, level_db) in enumerate(level_files, start=1):
        clip_id = f"clip_{idx:04d}"
        dest = LEVELS_DIR / f"{clip_id}.wav"
        shutil.copy2(path, dest)
        rows.append({
            "clip_id": clip_id,
            "category": category,
            "sample_id": sample_id,
            "level_db": level_db,
        })
    print(f"Copied {len(rows)} clips to {LEVELS_DIR}.")

    with open(SURVEY_MAPPING_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["clip_id", "category", "sample_id", "level_db"])
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {SURVEY_MAPPING_CSV}. Keep this file private; do not share with survey participants.")


if __name__ == "__main__":
    main()
