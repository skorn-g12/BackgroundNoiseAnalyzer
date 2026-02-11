"""
Read manifest_original.csv (or scan category dirs), generate 7 level-normalized WAVs
per original file at -40, -35, -30, -25, -20, -15, -10 dB, save as
{category}_{sample_id}_level_{db}db.wav. Avoid clipping (peak-limit if needed).
"""
import csv
from pathlib import Path

import numpy as np
import soundfile as sf

from config import (
    ROOT_DIR,
    CATEGORIES,
    SAMPLE_RATE,
    LEVELS_DB,
    MANIFEST_ORIGINAL_CSV,
)

EPS = np.finfo(float).eps
CLIP_THRESHOLD = 0.99


def load_audio(path: Path) -> np.ndarray:
    """Load mono audio as float64."""
    audio, _ = sf.read(path)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    return audio.astype(np.float64)


def rms(audio: np.ndarray) -> float:
    return float((audio ** 2).mean() ** 0.5)


def normalize_to_level_db(audio: np.ndarray, target_db: float) -> np.ndarray:
    """Scale audio so its RMS equals 10^(target_db/20). Peak-limit to avoid clipping."""
    current_rms = rms(audio)
    if current_rms <= 0:
        return audio
    target_rms = 10 ** (target_db / 20)
    scale = target_rms / (current_rms + EPS)
    out = audio * scale
    if np.any(np.abs(out) > CLIP_THRESHOLD):
        out = out / (np.max(np.abs(out)) / CLIP_THRESHOLD)
    return out.astype(np.float32)


def category_key(name: str) -> str:
    return name[0].lower() + name[1:] if name else name


def get_manifest_rows() -> list[dict]:
    """Read manifest_original.csv. If missing, build from category dirs."""
    if MANIFEST_ORIGINAL_CSV.exists():
        with open(MANIFEST_ORIGINAL_CSV, newline="") as f:
            return list(csv.DictReader(f))

    rows = []
    for category in CATEGORIES:
        cat_dir = ROOT_DIR / category
        if not cat_dir.exists():
            continue
        ckey = category_key(category)
        # Only consider base files like office_01.wav, not level_* variants
        for path in sorted(cat_dir.glob("*.wav")):
            if "_level_" in path.stem:
                continue
            if path.stem.startswith(ckey) and path.suffix.lower() == ".wav":
                # Infer sample_id from stem (e.g. office_01 -> 01)
                stem = path.stem
                if stem.startswith(ckey + "_"):
                    sample_id = stem[len(ckey) + 1:]
                    if sample_id.isdigit():
                        sample_id = f"{int(sample_id):02d}"
                    rows.append({
                        "category": category,
                        "sample_id": sample_id,
                        "filename": path.name,
                        "path": str(path),
                    })
    return rows


def main() -> None:
    rows = get_manifest_rows()
    if not rows:
        print("No manifest rows. Run process_originals.py first or add files to raw/<Category>/.")
        return

    for row in rows:
        path = Path(row["path"])
        if not path.exists():
            print(f"Skip missing: {path}")
            continue
        category = row["category"]
        sample_id = row["sample_id"]
        ckey = category_key(category)
        out_dir = ROOT_DIR / category
        out_dir.mkdir(parents=True, exist_ok=True)

        audio = load_audio(path)
        for target_db in LEVELS_DB:
            out_audio = normalize_to_level_db(audio, target_db)
            out_name = f"{ckey}_{sample_id}_level_{target_db}db.wav"
            out_path = out_dir / out_name
            sf.write(out_path, out_audio, SAMPLE_RATE)
        print(f"  {category} {sample_id}: wrote {len(LEVELS_DB)} level files")

    print("Done. Run build_survey_bundle.py to create levels/ and survey_mapping.csv.")


if __name__ == "__main__":
    main()
