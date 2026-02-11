"""
Load samples from raw/<Category>/, compute original RMS dB, trim to max duration,
resample to target SR, save into category dirs (Office/, Cafe/, ...), write manifest_original.csv.
"""
import csv
from pathlib import Path

import numpy as np
import soundfile as sf
import librosa

from config import (
    ROOT_DIR,
    CATEGORIES,
    RAW_DIR,
    SAMPLE_RATE,
    MAX_DURATION_SEC,
    MANIFEST_ORIGINAL_CSV,
    AUDIO_EXTENSIONS,
    SAMPLES_PER_CATEGORY,
)

EPS = np.finfo(float).eps


def load_audio(path: Path, target_sr: int) -> tuple[np.ndarray, int, float]:
    """Load audio, convert to mono, resample to target_sr. Returns (audio, sr, original_duration_sec)."""
    audio, sr = sf.read(path)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    original_duration = len(audio) / sr
    if sr != target_sr:
        audio = librosa.resample(audio.astype(np.float64), orig_sr=sr, target_sr=target_sr)
    return audio.astype(np.float64), target_sr, original_duration


def trim_to_max_duration(audio: np.ndarray, sr: int, max_sec: float) -> np.ndarray:
    """Keep only the first max_sec seconds."""
    n = int(sr * max_sec)
    if len(audio) <= n:
        return audio
    return audio[:n].copy()


def rms_dbfs(audio: np.ndarray) -> float:
    """RMS level in dB relative to full scale (dBFS)."""
    rms = (audio.astype(np.float64) ** 2).mean() ** 0.5
    return float(20 * np.log10(rms + EPS))


def category_key(name: str) -> str:
    """Category dir name -> lowercase key for filenames (e.g. Office -> office)."""
    return name[0].lower() + name[1:] if name else name


def main() -> None:
    for cat in CATEGORIES:
        (ROOT_DIR / cat).mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    key = category_key

    for category in CATEGORIES:
        raw_cat = RAW_DIR / category
        if not raw_cat.exists():
            print(f"Skip {category}: no raw dir {raw_cat}")
            continue

        files = []
        for ext in AUDIO_EXTENSIONS:
            files.extend(raw_cat.glob(f"*{ext}"))
        files = sorted(files)[:SAMPLES_PER_CATEGORY]

        if len(files) < SAMPLES_PER_CATEGORY:
            print(f"Warning: {category} has {len(files)} files (expected up to {SAMPLES_PER_CATEGORY})")

        out_cat = ROOT_DIR / category
        out_cat.mkdir(parents=True, exist_ok=True)
        ckey = key(category)

        for idx, path in enumerate(files, start=1):
            sample_id = f"{idx:02d}"
            try:
                audio, sr, orig_dur = load_audio(path, SAMPLE_RATE)
            except Exception as e:
                print(f"Error loading {path}: {e}")
                continue

            audio = trim_to_max_duration(audio, sr, MAX_DURATION_SEC)
            duration_sec = len(audio) / sr
            db = rms_dbfs(audio)

            out_name = f"{ckey}_{sample_id}.wav"
            out_path = out_cat / out_name
            sf.write(out_path, audio, sr)

            rows.append({
                "category": category,
                "sample_id": sample_id,
                "filename": out_name,
                "original_rms_db": round(db, 2),
                "duration_sec": round(duration_sec, 2),
                "path": str(out_path),
            })
            print(f"  {category} {sample_id}: {out_name}  original_rms_db={db:.2f}  duration_sec={duration_sec:.2f}")

    with open(MANIFEST_ORIGINAL_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["category", "sample_id", "filename", "original_rms_db", "duration_sec", "path"])
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {MANIFEST_ORIGINAL_CSV} ({len(rows)} rows).")


if __name__ == "__main__":
    main()
